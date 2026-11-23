"""Tests for skills/csharp/scripts/detect_target.py (no SDK probe, no network)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "csharp" / "scripts" / "detect_target.py"
spec = importlib.util.spec_from_file_location("detect_target", SCRIPT)
dt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dt  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(dt)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_solution(root: Path) -> None:
    write(
        root / "global.json",
        '{"sdk": {"version": "10.0.100", "rollForward": "latestFeature"},'
        ' "test": {"runner": "Microsoft.Testing.Platform"}}',
    )
    write(
        root / "Directory.Build.props",
        """<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <EfVersion>10.0.1</EfVersion>
  </PropertyGroup>
</Project>""",
    )
    write(
        root / "Directory.Packages.props",
        """<Project>
  <ItemGroup>
    <PackageVersion Include="Microsoft.EntityFrameworkCore.SqlServer" Version="$(EfVersion)" />
    <PackageVersion Include="xunit.v3" Version="3.1.0" />
  </ItemGroup>
</Project>""",
    )
    write(
        root / "src" / "Api" / "Api.csproj",
        """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" />
  </ItemGroup>
</Project>""",
    )
    write(
        root / "src" / "Lib" / "Lib.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>netstandard2.0;net8.0;net10.0</TargetFrameworks>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
</Project>""",
    )
    write(
        root / "tests" / "Api.Tests" / "Api.Tests.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net11.0</TargetFramework>
    <LangVersion>preview</LangVersion>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit.v3" />
  </ItemGroup>
</Project>""",
    )
    write(root / "src" / "Api" / "obj" / "Ignored.csproj", "<Project />")


def by_name(data: dict, name: str) -> dict:
    return next(p for p in data["projects"] if p["path"].endswith(name))


def test_defaults_and_stacks(tmp_path: Path) -> None:
    make_solution(tmp_path)
    data = dt.collect(tmp_path, probe=False)

    assert data["sdk"]["pinned"] == "10.0.100"
    assert data["sdk"]["max_lang_version"] == "14"
    assert data["sdk"]["test_runner"] == "Microsoft.Testing.Platform"
    assert len(data["projects"]) == 3  # obj/ is skipped

    api = by_name(data, "Api.csproj")
    assert api["lang_version"] == {"net10.0": "14"}
    assert api["stacks"]["efcore"] == "10.0.1"  # resolved through CPM and a property
    assert "aspnetcore" in api["stacks"]
    assert api["properties"]["Nullable"]["value"] == "enable"
    assert not api["preview"]


def test_latest_and_multi_targeting(tmp_path: Path) -> None:
    make_solution(tmp_path)
    lib = by_name(dt.collect(tmp_path, probe=False), "Lib.csproj")
    assert lib["target_frameworks"] == ["netstandard2.0", "net8.0", "net10.0"]
    # LangVersion=latest follows the SDK (10 -> C# 14) for every target framework.
    assert set(lib["lang_version"].values()) == {"14"}


def test_preview_is_flagged(tmp_path: Path) -> None:
    make_solution(tmp_path)
    tests = by_name(dt.collect(tmp_path, probe=False), "Api.Tests.csproj")
    assert tests["preview"]
    assert tests["test_frameworks"] == ["xUnit v3"]


def test_default_lang_table() -> None:
    assert dt.default_lang("net11.0") == "15"
    assert dt.default_lang("net9.0-windows10.0.19041.0") == "13"
    assert dt.default_lang("net48") == "7.3"
    assert dt.default_lang("netstandard2.0") == "7.3"


def test_conditional_property_is_reported(tmp_path: Path) -> None:
    write(
        tmp_path / "App.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net9.0</TargetFramework></PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)' == 'Release'">
    <LangVersion>13</LangVersion>
  </PropertyGroup>
</Project>""",
    )
    report = dt.collect(tmp_path / "App.csproj", probe=False)["projects"][0]
    assert report["lang_version"] == {"net9.0": "13"}
    assert any("condition" in note for note in report["notes"])


def test_file_based_app(tmp_path: Path) -> None:
    app = write(
        tmp_path / "tool.cs",
        "#!/usr/bin/env dotnet\n#:package Humanizer@2.14.1\n"
        "#:property LangVersion=preview\nConsole.WriteLine(1);\n",
    )
    data = dt.collect(app, probe=False)
    assert data["projects"] == []
    entry = data["file_based_apps"][0]
    assert entry["directives"]["package"] == ["Humanizer@2.14.1"]
    assert entry["lang_version"] == "preview"


def test_slnx_and_cli(tmp_path: Path) -> None:
    make_solution(tmp_path)
    write(tmp_path / "App.slnx", '<Solution><Project Path="src/Api/Api.csproj" /></Solution>')
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "App.slnx"), "--json", "--no-sdk-probe"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    data = json.loads(result.stdout)
    assert [Path(p["path"]).name for p in data["projects"]] == ["Api.csproj"]

    text = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--no-sdk-probe"],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    assert "net10.0: C# 14" in text
    assert "PREVIEW" in text


def test_global_json_with_comments(tmp_path: Path) -> None:
    write(
        tmp_path / "global.json",
        '{\n  // pinned for CI, see https://example.org/docs\n  "sdk": {"version": "11.0.100"}'
        " /* block */\n}",
    )
    write(tmp_path / "A.csproj", '<Project Sdk="Microsoft.NET.Sdk" />')
    data = dt.collect(tmp_path, probe=False)
    assert data["sdk"]["pinned"] == "11.0.100"
    assert data["sdk"]["max_lang_version"] == "15"


def test_lang_version_keywords_and_notes(tmp_path: Path) -> None:
    write(tmp_path / "global.json", '{"sdk": {"version": "9.0.100"}}')
    write(
        tmp_path / "Old.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <LangVersion>13</LangVersion>
  </PropertyGroup>
</Project>""",
    )
    write(
        tmp_path / "sub" / "Major.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <LangVersion>latestMajor</LangVersion>
  </PropertyGroup>
</Project>""",
    )
    write(
        tmp_path / "prev" / "Prev.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <EnablePreviewFeatures>true</EnablePreviewFeatures>
  </PropertyGroup>
</Project>""",
    )
    data = dt.collect(tmp_path, probe=False)
    old = by_name(data, "Old.csproj")
    assert any("newer than the net8.0 default" in n for n in old["notes"])

    major = by_name(data, "Major.csproj")
    assert major["lang_version"] == {"net10.0": "13"}  # follows the SDK, not the TFM
    assert any("follows the installed SDK" in n for n in major["notes"])
    assert any("cannot build net10.0" in n for n in major["notes"])

    prev = by_name(data, "Prev.csproj")
    assert prev["preview"]
    assert prev["lang_version"]["net9.0"].startswith("preview")


def test_custom_tfm_alias_is_flagged(tmp_path: Path) -> None:
    write(
        tmp_path / "A.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFrameworks>linux;mac</TargetFrameworks></PropertyGroup>
</Project>""",
    )
    report = dt.collect(tmp_path, probe=False)["projects"][0]
    assert any("custom TFM alias" in n for n in report["notes"])


@pytest.mark.skipif(shutil.which("dotnet") is None, reason="needs the .NET SDK")
def test_evaluate_uses_msbuild(tmp_path: Path) -> None:
    write(
        tmp_path / "A.csproj",
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFrameworks>net8.0;net10.0</TargetFrameworks></PropertyGroup>
</Project>""",
    )
    report = dt.collect(tmp_path, probe=True, evaluate=True)["projects"][0]
    if report["lang_version_source"] != "dotnet msbuild evaluation":
        pytest.skip("installed SDK cannot evaluate net10.0")
    assert report["lang_version"]["net8.0"] == "12.0"
    assert report["lang_version"]["net10.0"] == "14.0"
