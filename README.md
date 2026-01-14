<p align="center">
  <img src="assets/orbs.png" width="120" />
</p>

<h1 align="center">Orbs</h1>

<p align="center">
  Automation framework that grows with your team
</p>

---

## What is Orbs?

**Orbs** is an automation framework for **Web, Mobile (Appium), and API testing** designed to **grow with your team**.

Orbs supports different levels of automation maturity:

* Junior QA engineers can start with visual tools, record-and-playback, reusable keywords, and Studio-based workflows
* Senior engineers can work directly with code, CLI, and CI/CD pipelines without restrictions or license lock-in

Both approaches share the same execution engine and project structure, allowing teams to evolve their automation practices **without rewriting tests or migrating frameworks**.

---

## Philosophy

### 1. Tests are software, not scripts

Automation code should be designed, structured, reviewed, and evolved like production code — not copied scripts glued together over time.

### 2. Explicit is better than implicit

If something runs, it should be obvious:

* what is executed
* from where
* with which configuration

No silent defaults. No hidden behavior.

### 3. Structure before scale

Orbs enforces structure early so teams don’t pay technical debt later. Scaling automation should feel predictable, not painful.

### 4. One core, many interfaces

The same execution engine can be accessed via:

* CLI
* REST API
* Orbs Studio (GUI)

Different entry points, same behavior.

### 5. Tooling should assist, not hide reality

Generators, runners, and spy tools exist to accelerate work — not to obscure how automation actually works.

---

## Table of Contents

* [Core Capabilities](#core-capabilities)
* [Quick Start](#quick-start)
* [CLI Overview](#cli-overview)
* [Spy](#spy)
* [Project Structure](#project-structure)
* [Configuration](#configuration)
* [Documentation](#documentation)
* [Contributing](#contributing)
* [License](#license)

---

## Core Capabilities

* 📦 Project scaffolding with `orbs init`
* 🧱 Clear project structure for large test suites
* ⟳ Test suite, test case, feature, and step generation
* ▶️ Unified runner for `.feature`, `.yml`, and `.py`
* 🌐 REST API server for listing and scheduling executions
* 🕵️ Web & Mobile Spy for element inspection
* ⚙️ Typer-powered CLI
* 🧩 Extensible hooks and listeners

---

## Quick Start

```bash
pip install orbs-cli

orbs setup android
orbs init myproject
cd myproject

orbs create-feature login
orbs implement-feature login
orbs run features/login.feature
```

---

## CLI Overview

```bash
orbs setup android
orbs init <project>
orbs create-testsuite <name>
orbs create-testcase <name>
orbs create-feature <name>
orbs implement-feature <name>
orbs run <target>
orbs serve [--port <port>]
orbs spy
```

---

## Spy

Orbs provides an interactive **Web & Mobile Spy**, similar to Katalon's Object Spy, for inspecting elements and capturing locators.

```bash
orbs spy --web --url=https://example.com
orbs spy --mobile
```

📖 Full Spy documentation: [docs/spy.md](https://github.com/badrusalam11/orbs-cli/blob/main/docs/spy.md)

---

## Project Structure

```text
myproject/
├── features/
├── steps/
├── testcases/
├── testsuites/
├── listeners/
├── settings/
└── .env
```

---

## Configuration

Environment variables and properties are defined explicitly using `.env` and `settings/*.properties`.

```env
APP_PORT=5006
SERVER_URL=http://localhost:5006
```

📖 Full configuration guide: [docs/configuration.md](https://github.com/badrusalam11/orbs-cli/blob/main/docs/configuration.md)

---

## Documentation

Detailed documentation is available under the `docs/` directory:

* [Philosophy & Concepts](https://github.com/badrusalam11/orbs-cli/blob/main/docs/philosophy.md) - Framework principles and maturity levels
* [CLI Reference](https://github.com/badrusalam11/orbs-cli/blob/main/docs/cli-reference.md) - Complete command documentation
* [Web Testing](https://github.com/badrusalam11/orbs-cli/blob/main/docs/web-testing.md) - Browser automation guide
* [Mobile Testing](https://github.com/badrusalam11/orbs-cli/blob/main/docs/mobile-testing.md) - Android testing with Appium
* [API Testing](https://github.com/badrusalam11/orbs-cli/blob/main/docs/api-testing.md) - REST API testing guide
* [Spy Tool](https://github.com/badrusalam11/orbs-cli/blob/main/docs/spy.md) - Element inspection and capture
* [Architecture](https://github.com/badrusalam11/orbs-cli/blob/main/docs/architecture.md) - Technical design and patterns

**Start here:** [docs/philosophy.md](https://github.com/badrusalam11/orbs-cli/blob/main/docs/philosophy.md)

---

## Contributing

Contributions are welcome.

Please ensure:

* Templates and CLI commands are updated
* Documentation reflects behavior changes

---

## License

Licensed under the Apache License, Version 2.0.  
See the [LICENSE](https://github.com/badrusalam11/orbs-cli/blob/main/LICENSE) file for details.


---

## Contact

Built & maintained by **Muhamad Badru Salam** - QA Engineer (SDET)

* Repository: [https://github.com/badrusalam11/orbs-cli](https://github.com/badrusalam11/orbs-cli)
* Pypi: [https://pypi.org/project/orbs-cli](https://pypi.org/project/orbs-cli)
* GitHub: [https://github.com/badrusalam11](https://github.com/badrusalam11)
* LinkedIn: [https://www.linkedin.com/in/muhamad-badru-salam/](https://www.linkedin.com/in/muhamad-badru-salam/)
* Email: [muhamadbadrusalam760@gmail.com](mailto:muhamadbadrusalam760@gmail.com)
