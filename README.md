# ntciptool

Universal command-line tool for communicating with **Variable Message Signs (VMS)** using the **NTCIP** (National Transportation Communications for ITS Protocol) standard over **SNMP**.

Features are added incrementally – see the changelog below.

---

## Requirements

- Python 3.10+
- [`pysnmp`](https://pysnmp.readthedocs.io/)

```bash
pip install -r requirements.txt
```

---

## Usage

```
ntciptool [-h] [-p PORT] [-r COMMUNITY] [-w COMMUNITY] {brightness} ...
```

Running `ntciptool` with no arguments prints full help.

### Global options

| Option | Default | Description |
|---|---|---|
| `-p / --port` | `161` | SNMP UDP port |
| `-r / --read-community` | `public` | SNMP read community string |
| `-w / --write-community` | `administrator` | SNMP write community string |

---

## Commands

### `brightness`

Get or set **dmsIllumControl** (NTCIP 1203 §6.6).

```
ntciptool brightness [--mode MODE] IP [IP ...]
```

#### Brightness modes

| Mode | Value | Description |
|---|---|---|
| `other` | 1 | Vendor-specific behaviour |
| `photocell` | 2 | Automatic via photocell sensor |
| `timer` | 3 | Scheduled timer |
| `manual` | 4 | Manual indexed level (via dmsIllumManLevel) |
| `manualDirect` | 5 | Direct light-output percentage |
| `manualIndexed` | 6 | Indexed via separate control table |

#### Examples

```bash
# Show current brightness mode on two signs
ntciptool brightness 192.168.1.10 192.168.1.11

# Set brightness to photocell on one sign
ntciptool brightness --mode photocell 192.168.1.10

# Set brightness to manual on three signs with a custom write community
ntciptool brightness --mode manual \
         --write-community admin \
         192.168.1.10 192.168.1.11 192.168.1.12
```

#### Sample output (set mode)

```
────────────────────────────────────────────────────────────
  Host : 192.168.1.10
  Brightness (before) : photocell [2]
  Setting brightness  : manual [4]
  Brightness (after)  : manual [4]
  Result              : OK ✓
────────────────────────────────────────────────────────────
```

---

## OID Reference

| OID | Name | Standard |
|---|---|---|
| `1.3.6.1.4.1.1206.4.2.3.7.1` | dmsIllumControl | NTCIP 1203 |

---

## Planned features

- [ ] Message posting / MULTI string support
- [ ] Sign status / error reading
- [ ] Brightness level (manualDirect percentage)
- [ ] Pixel test
- [ ] Fan / temperature status

---

## Changelog

### 0.1.0
- Initial release
- `brightness` command: read or set `dmsIllumControl` on one or more signs
- Help output when no arguments are supplied
- Before/after verification on every write
