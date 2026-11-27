"""Copy as tests/test_stack.py (named apart here so the skill repository's pytest
never collects it). Unit tests of a Pulumi program in Python, with Pulumi's mocks: no cloud, no
state, no credentials (references/iac/pulumi.md). Adapt the import and the
assertions to the program; keep one behavior per test."""

import pulumi


class Mocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        return [f"{args.name}-id", args.inputs]

    def call(self, args: pulumi.runtime.MockCallArgs):
        return {}


pulumi.runtime.set_mocks(Mocks(), project="{{project}}", stack="staging", preview=False)

import infra  # noqa: E402 - the program, imported after the mocks are in place


@pulumi.runtime.test
def test_every_resource_group_is_tagged_with_its_environment():
    def check(tags):
        assert tags["environment"] == "staging"

    return infra.resource_group.tags.apply(check)
