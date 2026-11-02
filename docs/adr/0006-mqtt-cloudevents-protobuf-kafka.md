# ADR-0006: MQTT 5 with CloudEvents and Protobuf at the edge, Kafka as the platform backbone

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Field cameras sit on flaky mobile or radio links, may be offline for hours, and need per-device
identity. The platform needs a durable, replayable log that several consumers (stream processing,
lineage, archival, alerting) read independently.

## Decision drivers

- Device-friendly protocol with offline tolerance and per-device authorisation.
- Standard event metadata that survives protocol hops.
- Compact payloads with enforced schemas and safe evolution.
- Replay of history into new consumers.

## Considered options

1. Devices write directly to Kafka (rejected: heavy clients, poor fit for intermittent links and
   device identity).
2. NATS JetStream end to end (good, but a smaller IoT device ecosystem than MQTT).
3. **MQTT 5 at the edge, bridged by Pecten's own gateway into Kafka** (chosen).

## Decision outcome

- **Edge:** MQTT 5 to Eclipse Mosquitto with mutual TLS. Each device has a short-lived
  certificate; its identity becomes its username and topic ACLs restrict it to
  `pecten/v1/{site}/{device}/#`. QoS 1, persistent sessions, Last Will for liveness.
- **Envelope:** CloudEvents 1.0 in **binary mode** (attributes in MQTT 5 user properties, Protobuf
  bytes as the payload). `type` follows `org.pecten.<entity>.<verb>.v<major>`; `source` is
  `/sites/{site}/devices/{device}`; the W3C `traceparent` extension carries trace context.
- **Gateway (`pecten-gateway`, Rust):** shared subscriptions for horizontal scaling; validation
  (CloudEvents attributes, Protobuf decoding, protovalidate rules); enrichment from the device
  registry; idempotent, transactional Kafka producer; a dead-letter topic with reason codes.
- **Kafka 4.x** (KRaft) with Protobuf schemas in Apicurio Registry; the CloudEvents Kafka binding
  maps attributes to headers. Topics are partitioned by device for per-device ordering.
- **Delivery semantics:** at-least-once from the device (store-and-forward outbox), exactly-once
  *effect* downstream through UUIDv7 event IDs and de-duplication in the gateway and in staging
  models.

## Consequences

- Positive: realistic IoT architecture; standards at every hop; replay for free.
- Negative: two brokers to operate and a gateway to build. That is intended: the gateway is a
  core piece of data-engineering work in the roadmap (M9).

## Confirmation

- `buf breaking` and registry compatibility rules (backward transitive) in CI.
- Chaos tests: broker restarts and six-hour edge outages replay without loss or duplicates (M9.6).
- An AsyncAPI 3 document describes every channel (M16.7).
