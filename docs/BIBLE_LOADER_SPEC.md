# Bible Loader Specification

## Purpose

Define how Bible editions are discovered, selected, and loaded by future LionGateOS Bible applications.

The loader should allow multiple Bible editions to exist without changing the core Bible reading system.

## Loader Flow

Edition Registry -> Edition Metadata -> Bible Loader -> Bible Reader

## Responsibilities

The Bible loader should:

- read available editions
- verify edition metadata
- load selected Bible text
- enable supported features
- preserve edition separation

## Edition Selection

Required:
- King James Version
- LionGateOS Custom KJV

Optional:
- French editions
- Spanish editions
- future translations
- imported editions

## Feature Handling

Features are enabled according to edition metadata.

Examples:

KJV:
- Strong's enabled
- Red-letter enabled

LionGateOS Custom KJV:
- Strong's enabled
- Red-letter enabled

Louis Segond 1910:
- Strong's disabled initially
- Red-letter supported

## Future Support

The loader should eventually support:

- downloadable translations
- e-Sword imports
- OSIS files
- USFM files
- user-owned Bible files

## Design Goal

The Bible engine should grow by adding editions, not by rewriting the reader.
