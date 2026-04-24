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

def _build_user_exe(build_dir: Path) -> Path:
    """Run PyInstaller to produce the connectra_user executable.

    Returns the path to the built executable (or single-dir dist folder).
    Raises RuntimeError if the build fails.
    """
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


def _create_seed_license(seed_dir: Path, user_email: str, user_passcode: str) -> None:
    from connectra_core.license_auth import (
        PUBLIC_KEY_FILE_NAME,
        LICENSE_FILE_NAME,
        create_signed_license,
        write_license_file,
        write_public_key_file,
    )

    license_doc = create_signed_license(user_email, user_passcode)
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
    """
    include_seed = bool(user_email and user_passcode)

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
            _create_seed_license(seed_dir, user_email, user_passcode)

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
