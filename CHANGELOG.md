# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-12-13

### Added

- Initial release
- MQTT integration for Tasmota NeoPool devices
- Support for MQTT auto-discovery
- **Sensors:**
  - Water temperature
  - pH data, state, and pump status
  - Redox (ORP) data
  - Hydrolysis data (%, g/h), state, runtime statistics
  - Filtration mode and speed
  - Powerunit voltages and diagnostics
  - Connection statistics
- **Binary Sensors:**
  - Module presence (pH, Redox, Hydrolysis, Chlorine, Conductivity, Ionization)
  - Relay states (pH, Filtration, Light, Acid)
  - Water flow and tank level indicators
- **Switches:**
  - Filtration on/off
  - Light on/off
  - AUX1-AUX4 relays
- **Select entities:**
  - Filtration mode (Manual, Auto, Heating, Smart, Intelligent, Backwash)
  - Filtration speed (Slow, Medium, Fast)
  - Boost mode (Off, On, On Redox)
- **Number entities:**
  - pH Min/Max setpoints
  - Redox setpoint
  - Hydrolysis setpoint
- **Button:**
  - Clear error state
- Configuration flow with MQTT discovery support
- English translations
