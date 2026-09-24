# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Per-state (state_id / state_name) vs state-group rich filters, incl. workspace-level (multi-project) querysets."""

import pytest

from plane.db.models import Issue, Project, ProjectMember, State
from plane.utils.filters.filterset import IssueFilterSet


def _project(workspace, create_user, name, identifier):
    project = Project.objects.create(name=name, identifier=identifier, workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


def _state(project, name, group):
    return State.objects.create(name=name, group=group, color="#000000", project=project, workspace=project.workspace)


def _issue(project, create_user, name, state, priority="none"):
    return Issue.objects.create(
        name=name,
        project=project,
        workspace=project.workspace,
        created_by=create_user,
        state=state,
        priority=priority,
    )


@pytest.fixture
def data(db, workspace, create_user):
    alpha = _project(workspace, create_user, "State Filter Alpha", "SFA")
    beta = _project(workspace, create_user, "State Filter Beta", "SFB")
    # two "started" states in alpha, plus a same-named "In Review" state in beta
    alpha_progress = _state(alpha, "In Progress", "started")
    alpha_review = _state(alpha, "In Review", "started")
    alpha_done = _state(alpha, "Done", "completed")
    beta_review = _state(beta, "In Review", "started")

    _issue(alpha, create_user, "alpha-progress", alpha_progress, priority="high")
    _issue(alpha, create_user, "alpha-review", alpha_review, priority="high")
    _issue(alpha, create_user, "alpha-review-low", alpha_review, priority="low")
    _issue(alpha, create_user, "alpha-done", alpha_done)
    _issue(beta, create_user, "beta-review", beta_review)
    return {
        "workspace": workspace,
        "alpha_progress": alpha_progress,
        "alpha_review": alpha_review,
        "alpha_done": alpha_done,
        "beta_review": beta_review,
    }


def _filter(workspace, params):
    qs = Issue.objects.filter(workspace=workspace, name__in=_NAMES)
    fs = IssueFilterSet(data=params, queryset=qs)
    assert fs.is_valid(), fs.errors
    return set(fs.qs.values_list("name", flat=True))


_NAMES = ["alpha-progress", "alpha-review", "alpha-review-low", "alpha-done", "beta-review"]


@pytest.mark.unit
class TestStateIdFilter:
    def test_exact_state_excludes_other_states_in_same_group(self, data):
        assert _filter(data["workspace"], {"state_id__in": str(data["alpha_review"].id)}) == {
            "alpha-review",
            "alpha-review-low",
        }

    def test_exact_state_is_project_scoped_across_workspace(self, data):
        # same-named "In Review" state in another project must not match
        assert "beta-review" not in _filter(data["workspace"], {"state_id__in": str(data["alpha_review"].id)})

    def test_multiple_states_across_projects(self, data):
        ids = f"{data['alpha_review'].id},{data['beta_review'].id}"
        assert _filter(data["workspace"], {"state_id__in": ids}) == {
            "alpha-review",
            "alpha-review-low",
            "beta-review",
        }

    def test_state_group_still_matches_whole_group(self, data):
        assert _filter(data["workspace"], {"state_group__in": "started"}) == {
            "alpha-progress",
            "alpha-review",
            "alpha-review-low",
            "beta-review",
        }

    def test_state_and_state_group_combine_with_and(self, data):
        assert (
            _filter(
                data["workspace"],
                {"state_id__in": str(data["alpha_review"].id), "state_group__in": "completed"},
            )
            == set()
        )

    def test_state_combines_with_other_filters(self, data):
        assert _filter(
            data["workspace"],
            {"state_id__in": str(data["alpha_review"].id), "priority__in": "high"},
        ) == {"alpha-review"}


@pytest.mark.unit
class TestStateNameFilter:
    def test_state_name_matches_same_named_state_in_every_project(self, data):
        assert _filter(data["workspace"], {"state_name__in": "In Review"}) == {
            "alpha-review",
            "alpha-review-low",
            "beta-review",
        }

    def test_state_name_excludes_other_states_in_same_group(self, data):
        assert "alpha-progress" not in _filter(data["workspace"], {"state_name__in": "In Review"})

    def test_multiple_state_names(self, data):
        assert _filter(data["workspace"], {"state_name__in": "In Review,Done"}) == {
            "alpha-review",
            "alpha-review-low",
            "alpha-done",
            "beta-review",
        }

    def test_state_name_narrowed_by_project(self, data):
        project_id = str(data["beta_review"].project_id)
        assert _filter(data["workspace"], {"state_name__in": "In Review", "project_id__in": project_id}) == {
            "beta-review"
        }

    def test_unknown_state_name_matches_nothing(self, data):
        assert _filter(data["workspace"], {"state_name__in": "Does Not Exist"}) == set()
