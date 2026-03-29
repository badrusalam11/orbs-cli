<p align="center">
  <img src="https://raw.githubusercontent.com/badrusalam11/orbs-cli/refs/heads/main/assets/orbs.png" width="120" />
</p>

<h1 align="center">Orbs</h1>

<p align="center">
  Automation framework that grows with your team
</p>


## Welcome

**Orbs** is a modern automation framework for:

* 🌐 Web testing
* 📱 Mobile testing (Appium)
* 🔌 API testing

It’s designed for **real-world teams**, not just demos.

Whether you're just starting automation or already running complex CI/CD pipelines — Orbs adapts to you.

---

## Why Orbs?

Most automation tools force you to choose:

* Easy but limited
* Or powerful but complicated

**Orbs gives you both.**

* Junior QA → use visual tools, record & play, reusable keywords
* Senior QA → use code, CLI, CI/CD pipelines

Same project. Same engine. No migration.

---

## Core Idea

> Tests are software, not scripts.

Orbs treats automation like real engineering:

* Structured
* Maintainable
* Scalable

No messy scripts. No hidden magic.

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

## What You Get

* 📦 Project scaffolding (`orbs init`)
* 🧱 Clean folder structure
* ▶️ Unified runner (feature / yaml / python)
* 🌐 Built-in API server
* 🕵️ Web & Mobile Spy
* ⚙️ CLI-first workflow
* 🔌 Extensible hooks & listeners

---

## Documentation

Start exploring:

* 📘 [Philosophy](philosophy.md)
* ⚙️ [CLI Reference](cli-reference.md)
* 🌐 [Web Testing](web-testing.md)
* 📱 [Mobile Testing](mobile-testing.md)
* 🔌 [API Testing](api-testing.md)
* 🕵️ [Spy Tool](spy.md)
* 🧱 [Architecture](architecture.md)

---

## Example Project Structure

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

## Who Is This For?

* QA Engineers (manual → automation)
* SDET / Automation Engineers
* Teams scaling test automation
* Anyone tired of messy test scripts 😄

---

## Philosophy in One Line

> Structure early. Scale safely.

---

## Next Step

👉 Start with **[Philosophy](philosophy.md)** to understand how Orbs is designed.

Or jump straight into:

👉 **[CLI Reference](cli-reference.md)** if you just want to use it.

---

## Contributing

Contributions are welcome!

Make sure:

* Docs stay in sync with features
* CLI behavior is clearly explained

---

## License

Apache License 2.0

---

##  Author

Built by **Badru** (QA Engineer / SDET)

---

💬 *Orbs is not just a tool — it’s a way to build automation that doesn’t collapse when your project grows.*
