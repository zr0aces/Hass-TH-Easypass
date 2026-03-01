# Hass-TH-Easypass

> Home Assistant custom component that shows your **Thai Easy Pass** toll-card balance as a sensor.

![Home Assistant dashboard showing Easy Pass balance](show.png)

<p><a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=zr0aces&amp;repository=Hass-TH-Easypass&amp;category=integration" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store."></a></p>

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Click **Custom repositories** and add `zr0aces/Hass-TH-Easypass` with category **Integration**.
3. Search for **Thai Easy Pass Balance** and install it.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/easypass` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

Add the following to your `configuration.yaml`:

```yaml
sensor:
  - platform: easypass
    name: "easypass_balance"
    username: "user@gmail.com"
    password: "password"
    offset: "1"
    scan_interval: 300   # seconds between updates (optional, default 30 s)
```

| Option | Required | Description |
|--------|----------|-------------|
| `name` | ✅ | Unique name for the sensor entity |
| `username` | ✅ | Email address used to log in at thaieasypass.com |
| `password` | ✅ | Password for the account |
| `offset` | ✅ | Which card to display — `"1"` for the first card, `"2"` for the second, etc. |
| `scan_interval` | ❌ | How often (in seconds) to refresh the balance (recommended: `300`) |

### Multiple cards

If you have more than one Easy Pass card linked to the same account, create one sensor per card using a different `offset`:

```yaml
sensor:
  - platform: easypass
    name: "easypass_balance_1"
    username: "user@gmail.com"
    password: "password"
    offset: "1"
    scan_interval: 300
  - platform: easypass
    name: "easypass_balance_2"
    username: "user@gmail.com"
    password: "password"
    offset: "2"
    scan_interval: 300
```

---

## Troubleshooting

| Symptom | What to check |
|---------|---------------|
| Sensor shows `unavailable` or `Login Failed` | Verify credentials by logging in at [thaieasypass.com](https://www.thaieasypass.com) directly |
| Wrong card balance shown | Confirm the `offset` value matches the card position shown on the website |
| Sensor updates too slowly | Lower `scan_interval` (minimum ~120 s to avoid being blocked) |

For detailed error messages go to **Settings → System → Logs** and search for `easypass`.

---

## วิธีการใช้งาน (ภาษาไทย)

เพิ่มการตั้งค่าด้านล่างในไฟล์ `configuration.yaml`:

```yaml
sensor:
  - platform: easypass
    name: "easypass_balance"
    username: "user@gmail.com"
    password: "password"
    offset: "1"
    scan_interval: 300
```

`offset` คืออันดับของบัตรที่ต้องการแสดง (`"1"` = บัตรใบแรก, `"2"` = บัตรใบที่สอง และต่อไป)

หากมีหลายใบให้สร้าง sensor แยกสำหรับแต่ละบัตร โดยเปลี่ยน `name` และ `offset` ให้ต่างกัน

หากพบปัญหา entity แสดงค่า `unavailable` หรือ `Login Failed`:
1. ตรวจสอบ username/password โดยลองล็อกอินที่ [thaieasypass.com](https://www.thaieasypass.com) โดยตรง
2. ดู log ได้ที่ **Settings → System → Logs** แล้วค้นหาคำว่า `easypass`
