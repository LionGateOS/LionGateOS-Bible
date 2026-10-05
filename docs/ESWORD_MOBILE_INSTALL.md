# e-Sword Mobile Install Guide

This guide records mobile installation behavior that has actually been tested
for GD and GD+.

## iPad — e-Sword HD

### Verified direct import

Both current `.bbli` editions have been tested successfully in e-Sword HD on
iPad:

- `GD.bbli`
- `GD+.bbli`

Tested installation steps:

1. Save the desired `.bbli` file on the iPad.
2. Open the file from Safari or the Files app.
3. Tap **Share**.
4. Choose **e-Sword** from the share sheet.
5. Open e-Sword HD.
6. Select **GD** or **GD+** from the available Bible versions.

The user does not need to rebuild or convert the tested `.bbli` files.

### Verified GD behavior

- edition appears as **GD**
- complete GD Scripture loads
- Jesus speech displays in Royal Purple `#9B00FF`
- no inline Strong's numbers are present

### Verified GD+ behavior

- edition appears as **GD+**
- complete GD Scripture loads
- Jesus speech displays in Aqua `#00E5FF`
- Strong's numbers are present
- Strong's numbers remain clickable for lookup in the tested e-Sword HD build

## Desktop e-Sword

The repository also generates desktop `.bblx` packages:

- `GD.bblx`
- `GD+.bblx`

Desktop and mobile packages are generated from the same canonical GD Bible
source and must preserve the same 66-book / 31,102-verse coordinate system.

## iPhone — e-Sword LT

A simple direct-import workflow for the current GD/GD+ packages has not been
verified on iPhone in this project.

Do not describe iPhone direct installation as supported until it has been
tested successfully.

## Android — e-Sword for Android

A direct custom-module import workflow for the current GD/GD+ packages has not
been verified on Android in this project.

Do not describe Android sideloading as supported until it has been tested
successfully.

## Support rule

Only installation paths and rendering behavior that have been tested in the
target application should be described as verified.

Current verified mobile target:

**iPad running e-Sword HD**
