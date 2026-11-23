#!/usr/bin/env bash
# Writes the fixture project into the run's working directory.
set -euo pipefail

cat > 'Contact.cs' <<'FIXTURE'
namespace Contacts;

public class Contact
{
    public string Name { get; set; } = "";
}
FIXTURE

cat > 'Contacts.csproj' <<'FIXTURE'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
FIXTURE

