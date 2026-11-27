// Unit tests of a Pulumi program in TypeScript, with Pulumi's mocks: no cloud, no
// state, no credentials (references/iac/pulumi.md). Adapt the imports and the
// assertions to the program's exports; keep one behavior per test.
import * as pulumi from "@pulumi/pulumi";
import { beforeAll, describe, expect, it } from "vitest";

const valueOf = <T>(output: pulumi.Output<T>): Promise<T> =>
  new Promise((resolve) => output.apply(resolve));

describe("infrastructure", () => {
  let infra: typeof import("../index");

  beforeAll(async () => {
    await pulumi.runtime.setMocks(
      {
        newResource: (args) => ({ id: `${args.name}-id`, state: args.inputs }),
        call: (args) => args.inputs,
      },
      "{{project}}",
      "staging",
      false,
    );
    // Imported after the mocks, so the program registers its resources against them.
    infra = await import("../index");
  });

  it("tags every resource group with its environment", async () => {
    const tags = await valueOf(infra.resourceGroup.tags);
    expect(tags).toMatchObject({ environment: "staging" });
  });
});
