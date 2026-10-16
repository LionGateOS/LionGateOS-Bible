# GD-M06-A1 Enrichment Schema

## Purpose

Define the data fields for GD Bible enrichment processing.

This document defines structure only.
No archive originals, databases, or production findings are modified.

## Core Provenance

Required:

- finding_uid
- source document
- source hash
- quote
- collection
- extraction source

## Classification

Fields:

- topic
- issue category
- observation type

Initial categories:

- scripture reference
- translation
- wording
- terminology
- historical/context

## Scripture Reference Layer

Fields:

- raw scripture reference
- normalized scripture reference
- verification status
- verification evidence

Rules:

- Preserve raw references.
- Never silently repair.
- Normalization is separate from correction.

## AI Observation Layer

Fields:

- observation
- model used
- reasoning mode
- confidence
- generated timestamp

## Verification Layer

Fields:

- status
- reviewer/model
- evidence
- rejection reason

Possible states:

- unverified
- verified
- rejected
- needs review

## Design Principles

- Preserve provenance.
- Keep AI output separate from verified conclusions.
- Maintain reproducibility.
- Support future archive-wide processing.

## Current Status

Schema design only.
No corpus processing authorized.

