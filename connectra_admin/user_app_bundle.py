"""
Utilities for building a distributable User App installer bundle.

The generated zip contains:
  - The compiled connectra_user executable (built via PyInstaller).
  - An install script for Windows (Install_Connectra_User_App.bat / .ps1).
  - Optional signed user license + public key files for local authentication.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _candidate_user_exes() -> list[Path]:
    """Return likely locations for an already-built User app executable."""
    repo_root = Path(__file__).resolve().parent.parent
    exe_dir = Path(sys.executable).resolve().parent

    return [
        # When testing/building from the repository.
        repo_root / "connectra_user" / "dist" / "connectra_user.exe",
        # When Admin and User EXEs are extracted into the same release folder.
        exe_dir / "connectra_user.exe",
        # When running repo-built Admin from connectra_admin/dist.
        exe_dir.parent.parent / "connectra_user" / "dist" / "connectra_user.exe",
        # When running from a copied Admin EXE beside repo-style folders.
        exe_dir.parent / "connectra_user" / "dist" / "connectra_user.exe",
    ]


def _find_existing_user_exe() -> Path | None:
    """Find a prebuilt User app executable if one is available."""
    for candidate in _candidate_user_exes():
        if candidate.exists():
            return candidate
    return None


def find_existing_user_exe() -> Path | None:
    """Return the first available prebuilt User app executable."""
    return _find_existing_user_exe()


def _build_user_exe(build_dir: Path) -> Path:
    """Run PyInstaller to produce the connectra_user executable.

    Returns the path to the built executable (or single-dir dist folder).
    Raises RuntimeError if the build fails.
    """
    existing_exe = _find_existing_user_exe()
    if existing_exe:
        return existing_exe

    if getattr(sys, "frozen", False):
        searched = "\n".join(str(path) for path in _candidate_user_exes())
        raise RuntimeError(
            "Could not find connectra_user.exe to bundle.\n\n"
            "Place connectra_user.exe next to connectra_admin.exe, or use the "
            "repo dist output before building a user installer.\n\n"
            f"Searched:\n{searched}"
        )

    repo_root = Path(__file__).resolve().parent.parent
    spec_file = repo_root / "connectra_user" / "connectra_user.spec"
    main_script = repo_root / "connectra_user" / "main.py"

    dist_dir = build_dir / "dist"
    work_dir = build_dir / "build"

    if spec_file.exists():
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(spec_file),
            "--distpath", str(dist_dir),
            "--workpath", str(work_dir),
            "--noconfirm",
        ]
    else:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(main_script),
            "--name", "connectra_user",
            "--distpath", str(dist_dir),
            "--workpath", str(work_dir),
            "--noconfirm",
            "--onefile",
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"PyInstaller build failed:\n{result.stdout}\n{result.stderr}"
        )

    # Locate the produced binary/folder
    exe_candidates = list(dist_dir.rglob("connectra_user.exe")) + \
                     list(dist_dir.rglob("connectra_user"))

    if not exe_candidates:
        raise RuntimeError("PyInstaller succeeded but no output binary was found.")

    return exe_candidates[0]


def _create_seed_license(
    seed_dir: Path,
    user_email: str,
    user_passcode: str,
    mailbox_password: str | None = None,
    employee_id: str | None = None,
) -> None:
    """Create license seed files that bind a bundle to one user."""
    from connectra_core.license_auth import (
        PUBLIC_KEY_FILE_NAME,
        LICENSE_FILE_NAME,
        create_signed_license,
        write_license_file,
        write_public_key_file,
    )

    license_doc = create_signed_license(
        user_email,
        user_passcode,
        mailbox_password,
        employee_id=employee_id,
    )
    write_license_file(license_doc, seed_dir / LICENSE_FILE_NAME)
    write_public_key_file(seed_dir / PUBLIC_KEY_FILE_NAME)


def _write_install_scripts(staging_dir: Path, include_seed_files: bool) -> None:
    """Write the Windows install helper scripts into *staging_dir*."""

    seed_copy = (
        'copy /Y "%~dp0seed\\connectra_user_license.json" "%USERPROFILE%\\.connectra\\data\\connectra_user_license.json"\n'
        'copy /Y "%~dp0seed\\connectra_license_public_key.pem" "%USERPROFILE%\\.connectra\\data\\connectra_license_public_key.pem"'
    ) if include_seed_files else "rem No auth seed files included"

    seed_copy_ps = (
        'Copy-Item -Force "$PSScriptRoot\\seed\\connectra_user_license.json" "$env:USERPROFILE\\.connectra\\data\\connectra_user_license.json"\n'
        'Copy-Item -Force "$PSScriptRoot\\seed\\connectra_license_public_key.pem" "$env:USERPROFILE\\.connectra\\data\\connectra_license_public_key.pem"'
    ) if include_seed_files else "# No auth seed files included"

    bat_content = f"""\
@echo off
setlocal

set INSTALL_DIR=%USERPROFILE%\\.connectra
set DATA_DIR=%INSTALL_DIR%\\data

echo Installing Connectra User App...

if not exist "%INSTALL_DIR%\\bin" mkdir "%INSTALL_DIR%\\bin"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

xcopy /E /I /Y "%~dp0app" "%INSTALL_DIR%\\bin"

{seed_copy}

echo Installation complete.
echo You can launch the app from: %INSTALL_DIR%\\bin\\connectra_user.exe
pause
"""

    ps_content = f"""\
#Requires -Version 5.1
$InstallDir = "$env:USERPROFILE\\.connectra"
$DataDir    = "$InstallDir\\data"

Write-Host "Installing Connectra User App..."

New-Item -ItemType Directory -Force -Path "$InstallDir\\bin" | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

Copy-Item -Recurse -Force "$PSScriptRoot\\app\\*" "$InstallDir\\bin"

{seed_copy_ps}

Write-Host "Installation complete."
Write-Host "Launch the app from: $InstallDir\\bin\\connectra_user.exe"
"""

    (staging_dir / "Install_Connectra_User_App.bat").write_text(bat_content, encoding="utf-8")
    (staging_dir / "Install_Connectra_User_App.ps1").write_text(ps_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_user_app_bundle(
    output_zip_path: str,
    user_email: str | None = None,
    user_passcode: str | None = None,
    mailbox_password: str | None = None,
    employee_id: str | None = None,
) -> None:
    """Build a distributable installer zip for the Connectra User App.

    Parameters
    ----------
    output_zip_path:
        Destination path for the generated ``.zip`` file.
    user_email:
        If provided (together with *user_passcode*), signed license seed files
        are included in the zip for local authentication.
    user_passcode:
        User passcode used for local license validation. Ignored when
        *user_email* is ``None``.
    mailbox_password:
        Mailbox app password/key encrypted into the signed license for scan
        and send authentication.
    employee_id:
        Employee identifier embedded in the bootstrap license.
    """
    include_seed = bool(user_email and user_passcode)
    if include_seed and not employee_id:
        raise ValueError("Employee ID is required for a licensed bootstrap package.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. Build the user executable
        exe_path = _build_user_exe(tmp_path)

        # 2. Prepare staging layout
        staging = tmp_path / "staging"
        app_dir = staging / "app"
        app_dir.mkdir(parents=True)

        if exe_path.is_dir():
            shutil.copytree(str(exe_path), str(app_dir), dirs_exist_ok=True)
        else:
            shutil.copy2(str(exe_path), str(app_dir / exe_path.name))

        # 3. Seed local auth files (optional)
        if include_seed:
            seed_dir = staging / "seed"
            seed_dir.mkdir()
            _create_seed_license(
                seed_dir,
                user_email,
                user_passcode,
                mailbox_password,
                employee_id,
            )

        # 4. Write install scripts
        _write_install_scripts(staging, include_seed_files=include_seed)

        # 5. Zip the staging directory, preserving executable permissions
        output_zip_path = str(output_zip_path)
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in staging.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(staging)
                    info = zipfile.ZipInfo.from_file(str(file), arcname)
                    # Preserve Unix permissions (owner-executable bit) so the
                    # bundled binary remains runnable on Unix-like systems.
                    if file.stat().st_mode & 0o100:
                        info.external_attr |= (0o755 & 0xFFFF) << 16
                    with open(file, "rb") as fh:
                        zf.writestr(info, fh.read(), zipfile.ZIP_DEFLATED)
