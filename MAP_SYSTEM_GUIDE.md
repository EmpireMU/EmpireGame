# Interactive Map System Guide

## Overview
Your Empire game now has a complete interactive map system that allows you to upload high-resolution Wonderdraft maps, tile them for performance, and display them with Leaflet.js.

## How to Upload and Display Your Map

### Step 1: Upload Your Wonderdraft Map
1. Go to `/admin/upload-assets/` (or click "Upload Site Assets" in your admin menu)
2. Set **Asset Type** to **"World Map (full resolution, no resizing)"**
3. Enter a custom filename (e.g., `empire_world`) - optional but recommended
4. Select your 8192×4096 Wonderdraft PNG file
5. Click **Upload**

### Step 2: Generate Tiles
1. After upload, go to `/admin/manage-assets/`
2. Find your map in the list (it will show as "World Map | Not Tiled")
3. Click the **"Generate Tiles"** button
4. Wait 1-2 minutes for processing (creates ~500-1000 tiles)
5. Page will reload showing "Tiled" badge and **"View Map"** button

### Step 3: View Your Interactive Map
1. Click the **"View Map"** button
2. Your map opens in an interactive viewer with:
   - **Click & Drag** to pan
   - **Scroll** to zoom (6 zoom levels)
   - **Markers** for locations (when you add them)

## Adding Location Markers

You have two options for adding your clickable locations:

### Option A: Edit the Template Directly (Quick Start)
Edit `web/templates/website/map_viewer.html` around line 97:

```javascript
const exampleLocations = [
    { 
        name: "Realm of Norhame", 
        coords: [1200, 3500],  // [Y, X] coordinates
        description: "The northern realm of Norhame",
        type: "kingdom"
    },
    { 
        name: "Divine Assembly", 
        coords: [900, 4800],
        description: "The seat of divine power",
        type: "landmark"
    },
    // Add all 50+ locations here...
];
```

**Finding Coordinates:**
- Click anywhere on the map
- Check browser console (F12) for coordinates
- Use those values in your location data

### Option B: Database-Driven (Recommended for 50+ Locations)

Create a Django model to store locations:

```python
# web/worldinfo/models.py
class MapLocation(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    x_coord = models.IntegerField()
    y_coord = models.IntegerField()
    location_type = models.CharField(max_length=50)  # city, landmark, dungeon, etc.
    map_name = models.CharField(max_length=100)  # Which map this belongs to
```

Then update the view to pass locations to the template.

## Location Types and Marker Colors

Default marker colors:
- **City** (red): Major settlements
- **Town** (blue): Smaller settlements  
- **Dungeon** (purple): Dungeons and dangerous areas
- **Landmark** (orange): Points of interest
- **Default** (gray): Everything else

Customize colors in the `getMarkerIcon()` function in `map_viewer.html`.

## Technical Details

### File Structure
- **Original maps**: `server/media/site_assets/maps/[filename].png`
- **Tiles**: `server/media/site_assets/maps/[filename]_tiles/{z}/{x}/{y}.png`
- **Metadata**: `server/media/site_assets/maps/[filename]_tiles/metadata.json`

### Tiling Process
- Uses **PIL/Pillow** (already installed)
- Generates 6 zoom levels (0-5)
- 256×256 pixel tiles
- Takes ~1-2 minutes for 8K images
- Creates ~500-1000 tiles total

### Performance
- Only loads visible tiles (lazy loading)
- Much faster than loading full 20-50MB image
- Works great on mobile
- Smooth zoom/pan experience

## URLs

- **Upload**: `/admin/upload-assets/`
- **Manage**: `/admin/manage-assets/`
- **View Map**: `/map/[map_name]/`
  - Example: `/map/empire_world/`

## Next Steps

1. Upload your Wonderdraft map
2. Generate tiles
3. Click around to find coordinates for your 50+ locations
4. Add locations to the map (Option A for quick start)
5. Optionally create a database model for easier location management

## Tips

- Use descriptive filenames (e.g., `empire_world` not `map`)
- Keep original Wonderdraft file as backup
- Test on mobile to ensure good UX
- Consider grouping locations by type (kingdoms, cities, landmarks)
- You can add search functionality later using Leaflet plugins

## Advanced Features (Future)

Potential additions:
- **Search box** to find locations by name
- **Layer controls** to toggle location types
- **Polygon overlays** for kingdom boundaries
- **Travel routes** using polylines
- **Link to wiki pages** from markers
- **Admin interface** to add/edit markers without code

---

**Questions?** The system is fully functional and ready to use. Just upload your map and start adding markers!

