# Bible Edition Metadata Specification

## Purpose

Define the standard metadata format used by all LionGateOS Bible editions.

The goal is to allow multiple translations and editions to share the same Bible engine while keeping each edition clearly identified and documented.

## Required Metadata Fields

Each Bible edition should define:

- edition ID
- language
- display name
- short name
- edition type
- source information
- license information
- installation status
- supported features

## Example Metadata

Example edition metadata:

- id: louis_segond_1910
- language: fr
- name: Louis Segond 1910
- required: false
- red-letter support: true
- Strong's support: false
- notes: true
- highlights: true

## Edition Types

Possible edition types:

- core_translation
- custom_translation
- optional_translation
- imported_translation

## Required Editions

- King James Version
- LionGateOS Custom KJV

## Optional Editions

- French Louis Segond 1910
- Spanish translations
- future language editions
- user-imported editions

## Licensing Metadata

Each edition should record:

- source
- copyright status
- license type
- attribution requirements
- redistribution rules

## Future Compatibility

The metadata system should support:

- GrowDaily integration
- e-Sword exports
- additional languages
- downloadable Bible packages
- future Bible study tools
