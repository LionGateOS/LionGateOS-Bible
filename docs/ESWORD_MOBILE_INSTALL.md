# e-Sword Mobile Install Guide

This guide explains how to install the finished LionGateOS Bible module on mobile devices.

## Important distinction

There are two different situations:

1. **Desktop e-Sword**
   - This project already produces the desktop Bible module path.

2. **Mobile e-Sword**
   - Mobile installation is different from desktop.
   - Apple devices and Android devices do **not** use the same end-user path as desktop e-Sword.

---

## iPad — e-Sword HD

### Short answer

You **cannot** rely on an iPad user simply downloading the finished file from GitHub in Safari and importing it directly into e-Sword HD.

### Official path

According to the official e-Sword HD FAQ, making and loading your own module for iPad requires:

1. A **PC with e-Sword 12+**
2. The **e-Sword PC Module Conversion Utility**
3. Transfer to the iPad using **Apple File Sharing**
4. Restarting e-Sword HD so it imports the converted module

### What this means for end users

If a user only has an iPad, the official documentation does **not** describe a simple “download from GitHub to iPad and import directly” workflow.

### Practical recommendation

For iPad users, distribute clear instructions that say:

- the module must already be converted for e-Sword HD
- the user will still need the official Apple File Sharing transfer path described by e-Sword
- direct Safari/iCloud-only installation is not currently documented here as a supported path

---

## iPhone — e-Sword LT

### Short answer

You **cannot** rely on an iPhone user simply downloading the finished file from GitHub and importing it directly into e-Sword LT.

### Official path

According to the official e-Sword LT FAQ, making and loading your own module for iPhone requires:

1. A **PC with e-Sword 12+**
2. The **e-Sword PC Module Conversion Utility**
3. Transfer to the iPhone using **Apple File Sharing**
4. Restarting e-Sword LT so it imports the converted module

### What this means for end users

If a user only has an iPhone, the official documentation does **not** describe a simple direct-download install path from GitHub or iCloud Files into e-Sword LT.

---

## Android — e-Sword for Android

### Short answer

Android is also **not** documented here as a simple “download from GitHub and import directly into e-Sword” path.

### Official path

The official Android tutorial describes downloading modules through the app’s built-in download flow.
It does **not** provide a normal documented end-user workflow for sideloading user-made custom Bible modules from GitHub into the app.

### What this means for end users

A direct custom-module sideload workflow for ordinary Android users is not documented here as a normal supported path.

---

## Strong's and custom wording note

This project preserves the canonical 66-book / 31,100-verse structure and has continued rebuilding the desktop e-Sword output successfully.

However, some custom wording changes expand one original word into two or more displayed words.
That means the project preserves canonical structure and current alignment totals, but users should understand that mobile e-Sword installation and exact Strong's display behavior on mobile still need real-device verification.

---

## Best current practical guidance

- **Desktop users:** use the standard desktop module path from this repository.
- **iPad users:** expect the official PC conversion + Apple File Sharing workflow.
- **iPhone users:** expect the official PC conversion + Apple File Sharing workflow.
- **Android users:** do not assume a simple direct custom-module import path is supported.

If the mobile install path becomes easier or better verified in future testing, this document should be updated.
