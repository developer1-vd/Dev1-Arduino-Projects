# App Lab import zips

Ready-made zips for **Arduino App Lab → Import app**. Each zip holds one
app folder with `app.yaml` at `<AppName>/app.yaml`, which is the layout App
Lab accepts.

| Zip | App |
|---|---|
| `ButtonBuzzerLevelsApp.zip` | Hold a button to play the buzzer at 3 levels |
| `RandomBuzzerApp.zip` | Buzzer randomly jumps between low and high |
| `FarthestDistanceApp.zip` | Farthest distance + parking-sensor beeps |
| `VibroButtonLevelsApp.zip` | Hold a button to vibrate, barely to super |

## Import
1. On GitHub, open the zip file and click **Download raw file** (the ⬇
   button). Don't use the green **Code → Download ZIP** button: that zips the
   whole repository, so `app.yaml` ends up too deep and App Lab rejects it
   with "missing or misplaced app.yaml".
2. In App Lab, choose **Import app** and pick the downloaded zip.
3. Press **Run**.

## Rebuilding
After changing an app, rebuild the zips:

```bash
python make_zips.py
```

To zip an app by hand, zip the app **folder itself** (e.g. right-click
`RandomBuzzerApp` → Compress), not its parent folder or the files inside it
one by one.
