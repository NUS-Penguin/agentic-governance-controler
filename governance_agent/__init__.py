"""Governance Agent package.

Evaluates whether a structured workflow object (produced upstream by the
Workflow Agent) appears compliant with the governance policy documents in
./policies/. This package never receives raw customer requests, and never
invents regulations beyond what the policy documents contain.
"""
