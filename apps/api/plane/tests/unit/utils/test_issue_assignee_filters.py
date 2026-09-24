# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Assignee rich-filter support for the "None" (unassigned) sentinel."""

import pytest
from django.utils import timezone

from plane.db.models import Issue, IssueAssignee, Project, ProjectMember, User
from plane.utils.filters.converters import LegacyToRichFiltersConverter
from plane.utils.filters.filterset import IssueFilterSet


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Assignee Filter Project",
        identifier="AFP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def member(db):
    return User.objects.create(
        email="assignee-filter-member@plane.so",
        username="ada-assignee",
        first_name="Ada",
        last_name="Assignee",
    )


def _issue(project, create_user, name, priority="none"):
    return Issue.objects.create(
        name=name,
        project=project,
        workspace=project.workspace,
        created_by=create_user,
        priority=priority,
    )


def _assign(issue, user):
    return IssueAssignee.objects.create(issue=issue, assignee=user, project=issue.project)


@pytest.fixture
def issues(db, project, create_user, member):
    unassigned = _issue(project, create_user, "unassigned", priority="high")
    unassigned_low = _issue(project, create_user, "unassigned-low", priority="low")
    assigned = _issue(project, create_user, "assigned", priority="high")
    _assign(assigned, member)
    assigned_to_creator = _issue(project, create_user, "assigned-to-creator", priority="none")
    _assign(assigned_to_creator, create_user)
    soft_deleted_only = _issue(project, create_user, "soft-deleted-only", priority="high")
    row = _assign(soft_deleted_only, member)
    IssueAssignee.objects.filter(pk=row.pk).update(deleted_at=timezone.now())
    return {
        "unassigned": unassigned,
        "unassigned_low": unassigned_low,
        "assigned": assigned,
        "assigned_to_creator": assigned_to_creator,
        "soft_deleted_only": soft_deleted_only,
    }


def _filter(project, data):
    qs = Issue.objects.filter(project=project)
    fs = IssueFilterSet(data=data, queryset=qs)
    assert fs.is_valid(), fs.errors
    return set(fs.qs.values_list("name", flat=True))


@pytest.mark.unit
class TestAssigneeIdInUnassigned:
    def test_none_returns_issues_with_no_active_assignees(self, project, issues):
        assert _filter(project, {"assignee_id__in": "None"}) == {
            "unassigned",
            "unassigned-low",
            "soft-deleted-only",
        }

    def test_member_id_is_unchanged(self, project, issues, member):
        assert _filter(project, {"assignee_id__in": str(member.id)}) == {"assigned"}

    def test_none_or_member(self, project, issues, member):
        assert _filter(project, {"assignee_id__in": f"None,{member.id}"}) == {
            "unassigned",
            "unassigned-low",
            "soft-deleted-only",
            "assigned",
        }

    def test_none_and_priority_narrows(self, project, issues):
        assert _filter(project, {"assignee_id__in": "None", "priority__in": "high"}) == {
            "unassigned",
            "soft-deleted-only",
        }

    def test_invalid_non_uuid_does_not_error_and_matches_nothing(self, project, issues):
        assert _filter(project, {"assignee_id__in": "not-a-uuid"}) == set()

    def test_invalid_value_is_ignored_when_mixed_with_a_member(self, project, issues, member):
        assert _filter(project, {"assignee_id__in": f"not-a-uuid,{member.id}"}) == {"assigned"}


@pytest.mark.unit
class TestLegacyAssigneeNoneConversion:
    def test_none_survives_legacy_to_rich_conversion(self):
        converted = LegacyToRichFiltersConverter().convert({"assignees": ["None"]})
        assert converted == {"assignee_id__in": "None"}

    def test_none_is_kept_alongside_a_member_id(self):
        member_id = "550e8400-e29b-41d4-a716-446655440001"
        converted = LegacyToRichFiltersConverter().convert({"assignees": ["None", member_id]})
        assert converted == {"assignee_id__in": f"None,{member_id}"}
