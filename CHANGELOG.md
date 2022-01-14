# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.0]

Initial release of s1-enumerator, a package for enumerating Sentinel-1 A/B pairs
for interferograms:
 * `s1_enumerator`, a `pip` installable python package that runs the enumeration


## [0.1.0]

Small updates to improve use:
 * add a `hash-id` when distilling data for API-submission. The hash-id is lossy
 hash derived from concantenation of reference and secondary SLC ids to more easily
 de-duplicate jobs.
