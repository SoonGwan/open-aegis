import { test } from "node:test";
import assert from "node:assert/strict";
import {
  blankRule,
  draftsToRules,
  parseRules,
  parseSchema,
  rulesToDrafts,
} from "../src/policy-rules.ts";

test("policy forms round-trip schema, owner and false permissions without UI keys", () => {
  const rows = [
    {
      path: "/api/account",
      role: "fixture",
      expected_allowed: false,
      credential_env: "AEGIS_TEST_FIXTURE",
      response_schema: {
        type: "object",
        properties: { tenant_id: { type: "string" } },
      },
      ownership: { pointer: "/tenant_id", expected: "fixture-owner" },
    },
  ];
  assert.deepEqual(draftsToRules(rulesToDrafts(rows)), rows);
  assert.deepEqual(
    draftsToRules([blankRule("not-an-exported-id")])[0].ownership,
    null,
  );
  const draft = rulesToDrafts(rows)[0];
  draft.schemaEnabled = false;
  draft.schema = "invalid inactive draft";
  draft.ownerEnabled = false;
  assert.equal(draftsToRules([draft])[0].response_schema, null);
  assert.equal(draftsToRules([draft])[0].ownership, null);
});

test("advanced fields cannot silently disappear when switching to a form", () => {
  const rows = [
    {
      path: "/",
      role: "fixture",
      expected_allowed: false,
      future_field: { important: true },
    },
  ];
  const original = JSON.stringify(rows);
  assert.throws(() => rulesToDrafts(rows), /JSON 편집/);
  assert.deepEqual(parseRules(original), rows);
  assert.equal(JSON.stringify(rows), original);
  assert.throws(() =>
    rulesToDrafts([{ path: "/", role: "fixture", expected_allowed: "false" }]),
  );
});

test("invalid JSON, counts, schema shapes and UTF-8 byte size reject serialization", () => {
  for (const text of [
    "{",
    "{}",
    "[null]",
    JSON.stringify(Array.from({ length: 21 }, () => ({}))),
  ])
    assert.throws(() => parseRules(text));
  for (const text of [
    "",
    "[]",
    "false",
    JSON.stringify({ const: "한".repeat(6000) }),
  ])
    assert.throws(() => parseSchema(text));
  const draft = blankRule("fixture");
  draft.schemaEnabled = true;
  draft.schema = "{";
  assert.throws(() => draftsToRules([draft]));
});
