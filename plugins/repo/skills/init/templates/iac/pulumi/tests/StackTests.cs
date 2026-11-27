// Unit tests of a Pulumi program in C#, with Pulumi's mocks: no cloud, no state,
// no credentials (references/iac/pulumi.md). Adapt the stack type and the
// assertions to the program; keep one behavior per test.
using System.Collections.Immutable;
using Pulumi;
using Pulumi.Testing;
using AwesomeAssertions;

namespace {{package}}.Infra.Tests;

public sealed class StackTests
{
    [Fact]
    public async Task Every_resource_is_tagged_with_its_environment()
    {
        ImmutableArray<Resource> resources = await Deployment.TestAsync<AppStack>(
            new Mocks(),
            new TestOptions { ProjectName = "{{project}}", StackName = "staging", IsPreview = false });

        var groups = resources.OfType<Pulumi.AzureNative.Resources.ResourceGroup>().ToArray();
        groups.Should().NotBeEmpty();
        foreach (var group in groups)
        {
            var tags = await group.Tags.GetValueAsync(whenUnknown: ImmutableDictionary<string, string>.Empty);
            tags.Should().ContainKey("environment").WhoseValue.Should().Be("staging");
        }
    }

    private sealed class Mocks : IMocks
    {
        public Task<(string? id, object state)> NewResourceAsync(MockResourceArgs args) =>
            Task.FromResult<(string?, object)>(($"{args.Name}-id", args.Inputs));

        public Task<object> CallAsync(MockCallArgs args) => Task.FromResult<object>(args.Args);
    }
}
