A fulfilment client moves an order to `Packed` or `Shipped` through a new `PUT /api/v1/orders/{orderNumber}/state`: one repository call checks the move and writes the state and an optional note, and anything else is refused with nothing changed. Highest risk: the transition rule is new code on the order lifecycle. Refusable: `Cancelled` is not settable here; a repeat of the current state succeeds; the note is trimmed and cleared when none is sent; no ADR. Hold-out declined by human: the expected values in the `Hold-out` block are yours to recompute by hand.
Risk: high-risk · contract: additive · ADR: none · red pause: phased · hold-out: required: 2 sealed tests from human
Business requirement: A fulfilment client can move an order to Packed (40) or Shipped (50); a paid order (30) may only move to Packed, and no order moves backwards.
Intended behavior: `PUT /api/v1/orders/{orderNumber}/state` with `{ state ∈ {Packed, Shipped}, note? }` answers `204` and writes the order's state and note; an unknown order answers `404` `order-not-found`; a refused move answers `409` `state-change-not-allowed`; a state outside the settable set or a note over 500 characters answers `400`.

BLOCKING - I will not guess: none — nothing is open.
Proceeding unless you object
- `Cancelled` and every state below `Packed` are not settable through this route.
- A repeat is harmless: 40 → 40 and 50 → 50 succeed and rewrite the same values.
- The note is trimmed, limited to 500 characters, and stored as empty when none is sent.
- The transition check and the write sit in one repository call, `IOrderRepository.SetStateAsync`.
- The handler reads the recognised clients from `OrderRoutesSettings`, bound to `Orders:Routes`, as the two queue jobs read them.

Risk level: high-risk - a new write into the order lifecycle with a state-machine rule.

Existing behavior
Orders are read-only through this service today. `GET /api/v1/orders/{orderNumber}` returns the order or `404`, which `GetOrder_ForAnUnknownNumber_Returns404` in `tests/Shop.Api.IntegrationTests/OrderEndpointTests.cs` holds in place, and the repository read behind it is held by `Get_ReturnsTheOrder_ForAKnownNumber` in `tests/Shop.Persistence.IntegrationTests/OrderRepositoryTests.cs`. Nothing writes an order's state from outside, and no test covers a move between states.

Behavior flow
The request is one straight path: validate, check the move and write in one call, answer.
Current flow: none — greenfield
Flow after change
1. (new) The client calls `PUT /api/v1/orders/{orderNumber}/state` with a state and an optional note.
2. (new) A state outside `Packed` and `Shipped`, or a note over 500 characters, is refused with `400` and nothing is read.
3. (new) The order is looked up; an unknown number answers `404` `order-not-found`.
4. (new) The move is allowed from Paid to Packed, from Packed to Packed or Shipped, and from Shipped to Shipped; anything else answers `409` `state-change-not-allowed` with the order unchanged.
5. (new) An allowed move writes the state and the trimmed note and answers `204`.
Unchanged adjacent paths
- Reading an order is untouched.

Known gaps
- No consumer contract exists for the fulfilment client; only this repository's API tests pin the route.

Assumptions
- A paid order has state 30, a packed one 40, a shipped one 50, as `OrderState` declares them.
- The fulfilment client is the only caller.

Uncovered or ambiguous
- Concurrent moves of one order are not addressed; the last write wins, as it does for every other order write.

New-behavior tests
- `Set_MovesAPaidOrderToPacked_AndStoresTheNote` — positive, side effect
  - covers: 30 → 40 succeeds; the state is 40 and the note is the sent text, trimmed.
  - path: `tests/Shop.Persistence.IntegrationTests/OrderStateRepositoryTests.cs`.
  - red: the stub reports `Set` and writes nothing, so the state is still 30.
- `Set_RefusesShipped_ForAPaidOrder` — negative
  - covers: 30 → 50 reports `NotAllowed`; the state and the note are unchanged.
  - path: `tests/Shop.Persistence.IntegrationTests/OrderStateRepositoryTests.cs`.
  - red: the stub reports `Set`.
- `SetOrderStateValidator_RejectsANoteOverTheLimit` — boundary
  - covers: a `note` of 501 characters is rejected with `request-validation-failed`; 500 characters pass.
  - path: `tests/Shop.Application.UnitTests/Orders/SetOrderStateValidatorTests.cs`.
  - red: the stub validator has no rules.
- `Handle_ReturnsConflict_WhenTheMoveIsNotAllowed` — error path
  - covers: the repository reports `NotAllowed`; the result is `409` `state-change-not-allowed`.
  - path: `tests/Shop.Application.UnitTests/Orders/SetOrderStateHandlerTests.cs`.
  - red: the stub handler answers success.
- `SetOrderState_ForAnAllowedMove_Returns204AndWritesTheState` — positive
  - covers: `PUT` with `{ "state": "Packed", "note": "boxed" }` on a paid order answers `204`; the state is 40.
  - path: `tests/Shop.Api.IntegrationTests/OrderStateEndpointTests.cs`.
  - red: nothing writes the state yet, so it is still 30.
- `SetOrderState_WithAStateOutsideTheSettableSet_Returns400` — negative
  - covers: `{ "state": "Cancelled" }` answers `400` and the order is unchanged.
  - path: `tests/Shop.Api.IntegrationTests/OrderStateEndpointTests.cs`.
  - red: the stub handler answers success, so the answer is `204`.

Case coverage not reached
- authorization — n/a — the route joins the existing versioned group and its policy; no route-level authorization test exists for that group.

Preservation pins
- `Get_ReturnsTheOrder_ForAKnownNumber` — legacy behavior
  - covers: the repository read is unchanged by the new write member.
  - path: `tests/Shop.Persistence.IntegrationTests/OrderRepositoryTests.cs`.
- `GetOrder_ForAnUnknownNumber_Returns404` — legacy behavior
  - covers: the sibling read route still binds and answers.
  - path: `tests/Shop.Api.IntegrationTests/OrderEndpointTests.cs`.
- `OpenApiDocument_PublishesNoEmptySummaryOrDescription` — legacy behavior
  - covers: the new operation is described in the public document.
  - path: `tests/Shop.Api.IntegrationTests/OpenApiDocumentTests.cs`.

Contract changes
- `docs/api/shop-openapi-v1.json` — new operation `SetOrderState`, `PUT /api/v1/orders/{orderNumber}/state`, with schema `SetOrderStateCommand` carrying `state` and an optional `note`; responses `204`, `400`, `404`, `409`; compatibility: additive; consumers: none — the fulfilment client is not built yet.

NFR budgets
- latency/throughput: unchanged — one repository call per request.
- authorization: unchanged — the group's existing policy applies.
- observability: one Information log line per accepted move.

Implementation slices
- Evidence order: the contract first, then the pins, then the new-behavior tests against compile-only stubs.
- Phase 1, the write — `src/Shop.Persistence/OrderRepository.cs` `SetStateAsync` checks the move and writes; turns green: `Set_MovesAPaidOrderToPacked_AndStoresTheNote`, `Set_RefusesShipped_ForAPaidOrder`.
- Phase 2, the command — `src/Shop.Application/Features/Orders/SetOrderStateCommandValidator.cs` rules and `src/Shop.Application/Features/Orders/SetOrderStateCommandHandler.cs` outcome mapping; turns green: `SetOrderStateValidator_RejectsANoteOverTheLimit`, `Handle_ReturnsConflict_WhenTheMoveIsNotAllowed`.
- Phase 3, the route — `src/Shop.Api/Endpoints/OrderEndpoints.cs` maps `SetOrderState` with its declared responses; turns green: `SetOrderState_ForAnAllowedMove_Returns204AndWritesTheState`, `SetOrderState_WithAStateOutsideTheSettableSet_Returns400`.

Verification
- `python tools/run.py build` — expected: `Build succeeded`.
- `python tools/run.py test --filter OrderState` — expected: the six new tests pass.
- `python tools/run.py test --filter "Get_ReturnsTheOrder_ForAKnownNumber|GetOrder_ForAnUnknownNumber_Returns404|OpenApiDocument_PublishesNoEmptySummaryOrDescription"` — expected: the three pins pass.
- `python tools/run.py test` — expected: the whole suite passes.
- `python tools/run.py openapi --check` — expected: the snapshot matches the routes.

Hold-out
- decision: required
- reason: state-machine semantics: which starting states admit which target.
- request: 2 sealed tests. (1) An order at Shipped (50) asked to move to Packed (40): assert the HTTP status and the order's state afterwards, computed by you from the requirement. (2) An order at Packed (40) asked to move to Packed again: assert the status and the stored note. Your own words, not the names above.
- options: `write` — 2 assertions, ~10 minutes; `decline` — recorded as `declined by human`, and this plan then lists the values you must verify by hand.
- recommended: `write` — the transition table was derived by this session from the same requirement the implementation reads.
- storage: outside this repository, unavailable to this session
- runner: you, against the branch once the visible suite is green
- result: declined by human — a waiver, not a pass
- human-verified expected values: recompute each by hand from the business requirement, not from the code: (1) Shipped (50) → Packed (40): `409` `state-change-not-allowed`, the order stays 50; (2) Packed (40) → Packed (40): `204`, the stored note is replaced by the sent one; (3) Paid (30) → Shipped (50): `409` `state-change-not-allowed`, the order stays 30.

Files likely to change
- `docs/api/shop-openapi-v1.json` — the new operation.
- `src/Shop.Application/Abstractions/IOrderRepository.cs` — gains `SetStateAsync`.
- `src/Shop.Application/Features/Orders/OrderStateOutcome.cs` — `Set`, `NotFound`, `NotAllowed`.
- `src/Shop.Application/Features/Orders/OrderStateChange.cs` — the outcome and the previous state.
- `src/Shop.Application/Features/Orders/SettableOrderState.cs` — the settable set.
- `src/Shop.Application/Features/Orders/SetOrderStateCommand.cs` — the request.
- `src/Shop.Application/Features/Orders/SetOrderStateCommandValidator.cs` — the field rules.
- `src/Shop.Application/Features/Orders/SetOrderStateCommandHandler.cs` — the outcome mapping and the log line.
- `src/Shop.Persistence/OrderRepository.cs` — `SetStateAsync`.
- `src/Shop.Api/Endpoints/OrderEndpoints.cs` — the route.
- `tests/Shop.Persistence.IntegrationTests/OrderStateRepositoryTests.cs` — two tests.
- `tests/Shop.Application.UnitTests/Orders/SetOrderStateValidatorTests.cs` — one test.
- `tests/Shop.Application.UnitTests/Orders/SetOrderStateHandlerTests.cs` — one test.
- `tests/Shop.Api.IntegrationTests/OrderStateEndpointTests.cs` — two tests.

Residual risk
- Concurrent moves of one order are last-write-wins.
- The hold-out was declined: the transition table rests on this session's reading plus your hand check of the listed values.
