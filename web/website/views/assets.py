def _storage_makedirs(path):
    """Ensure directories exist in storage."""
    if default_storage.exists(path):
        return
    try:
        os_path = default_storage.path(path)
        os.makedirs(os_path, exist_ok=True)
    except (NotImplementedError, AttributeError):
        parts = path.strip('/').split('/') if path else []
        current = ''
        for part in parts:
            current = _storage_join(current, part) if current else part
            if not default_storage.exists(current):
                placeholder = _storage_join(current, '.keep')
                default_storage.save(placeholder, ContentFile(b''))


def _delete_storage_tree(root_path):
    """Recursively delete files under storage path."""
    if not default_storage.exists(root_path):
        return

    try:
        shutil_path = default_storage.path(root_path)
        shutil.rmtree(shutil_path, ignore_errors=True)
        return
    except (NotImplementedError, AttributeError):
        pass

    # Fallback: manually walk using storage listdir
    dirs, files = default_storage.listdir(root_path)
    for file_name in files:
        file_path = _storage_join(root_path, file_name)
        default_storage.delete(file_path)
    for directory in dirs:
        dir_path = _storage_join(root_path, directory)
        _delete_storage_tree(dir_path)

    # After contents removed, delete directory placeholder if exists
    if default_storage.exists(root_path):
        default_storage.delete(root_path)


def _rename_storage_tree(old_path, new_path):
    """Rename/move storage directory recursively."""
    if not default_storage.exists(old_path):
        return

    try:
        old_fs = default_storage.path(old_path)
        new_fs = default_storage.path(new_path)
        shutil.move(old_fs, new_fs)
        return
    except (NotImplementedError, AttributeError):
        pass

    _delete_storage_tree(new_path)

    dirs, files = default_storage.listdir(old_path)
    for directory in dirs:
        source_dir = _storage_join(old_path, directory)
        target_dir = _storage_join(new_path, directory)
        _rename_storage_tree(source_dir, target_dir)

    for file_name in files:
        source_file = _storage_join(old_path, file_name)
        target_file = _storage_join(new_path, file_name)
        _storage_makedirs(os.path.dirname(target_file))
        with default_storage.open(source_file, 'rb') as src, default_storage.open(target_file, 'wb') as dst:
            dst.write(src.read())
        default_storage.delete(source_file)

    if default_storage.exists(old_path):
        default_storage.delete(old_path)
"""Views for site asset upload, management, and map tiling."""

import io
import json
import math
import os
import shutil
import uuid
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_http_methods

from PIL import Image, ImageOps
from PIL.Image import LANCZOS

from web.roster.views import resize_image


def _storage_join(*parts):
    """Join storage path components using forward slashes."""
    cleaned = []
    for part in parts:
        if not part:
            continue
        cleaned_part = str(part).strip('/\\')
        if cleaned_part:
            cleaned.append(cleaned_part)
    return '/'.join(cleaned)

def resize_image_with_transparency(image_file, max_size):
    """Resize image while preserving transparency for logos and graphics."""
    img = Image.open(image_file)
    
    # Resize while preserving the original mode (including transparency)
    img.thumbnail((max_size, max_size), LANCZOS)
    
    # Save as PNG to preserve transparency
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    return buffer

@staff_member_required
def upload_site_asset(request):
    if request.method == 'POST':
        if 'asset' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        asset_file = request.FILES['asset']
        asset_type = request.POST.get('type', 'logo')  # logo, icon, map, etc.
        custom_name = request.POST.get('custom_name', '')  # Optional custom filename
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        ext = os.path.splitext(asset_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'error': 'Invalid file type'}, status=400)
        
        # Handle maps separately - no resizing, preserve full resolution
        if asset_type == 'map':
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return JsonResponse({'error': 'Map uploads must be raster images (jpg, png, gif, webp).'}, status=400)
            try:
                # Use custom name if provided, otherwise generate one
                if custom_name:
                    extension = ext if ext != '.jpeg' else '.jpg'
                    filename = f"{custom_name}{extension}"
                else:
                    extension = ext if ext != '.jpeg' else '.jpg'
                    filename = f"map_{uuid.uuid4()}{extension}"
                
                # Save at full resolution
                path = f"site_assets/maps/{filename}"
                saved_path = default_storage.save(path, asset_file)
                
                url = default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}"
                actual_filename = os.path.basename(saved_path)
                
                return JsonResponse({
                    'success': True,
                    'filename': actual_filename,
                    'url': url,
                    'path': saved_path,
                    'is_map': True,
                    'message': 'Map uploaded successfully. Click "Generate Tiles" to make it interactive.'
                })
            except Exception as e:
                return JsonResponse({'error': f'Could not save map: {e}'}, status=400)
        
        # Handle SVG files - save directly without processing
        if ext == '.svg':
            try:
                # Use custom name if provided, otherwise use type + UUID
                if custom_name:
                    filename = f"{custom_name}.svg"
                else:
                    filename = f"{asset_type}_{uuid.uuid4()}.svg"
                
                # Save SVG directly without processing
                path = f"site_assets/{filename}"
                saved_path = default_storage.save(path, asset_file)
                
                url = default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}"
                actual_filename = os.path.basename(saved_path)
                
                return JsonResponse({
                    'success': True,
                    'filename': actual_filename,
                    'url': url,
                    'path': saved_path,
                    'message': 'SVG uploaded successfully.'
                })
            except Exception as e:
                return JsonResponse({'error': f'Could not save SVG: {e}'}, status=400)
        
        # Handle regular raster assets (logos, icons, etc.)
        # Determine if we should preserve transparency (use 'logo' for any graphic needing transparency)
        preserve_transparency = asset_type == 'logo'
        
        default_extension = '.png' if preserve_transparency else '.jpg'

        # Use custom name if provided, otherwise use type + UUID
        if custom_name:
            filename = f"{custom_name}{default_extension}"
        else:
            filename = f"{asset_type}_{uuid.uuid4()}{default_extension}"
        
        # Resize the image (800px max)
        try:
            if preserve_transparency:
                # For logos and graphics, preserve transparency
                compressed_buffer = resize_image_with_transparency(asset_file, 800)
            else:
                # For other assets, use white background like character images
                compressed_buffer = resize_image(asset_file, 800, good_quality=True)
            
            path = f"site_assets/{filename}"
            saved_path = default_storage.save(path, ContentFile(compressed_buffer.read()))
        except Exception as e:
            return JsonResponse({'error': f'Could not process image: {e}'}, status=400)
        
        url = default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}"
        
        # Extract the actual saved filename (Django may have modified it if file existed)
        actual_filename = os.path.basename(saved_path)
        
        return JsonResponse({
            'success': True,
            'filename': actual_filename,  # Return the actual saved filename
            'url': url,
            'path': saved_path
        })
    
    return render(request, 'website/upload_assets.html')

@staff_member_required
def manage_site_assets(request):
    """View to list and manage all site assets."""
    site_assets_dir = 'site_assets/'
    files = []
    
    try:
        # List all files in the site_assets directory

        directories, filenames = default_storage.listdir(site_assets_dir)

        for filename in filenames:
            file_path = _storage_join(site_assets_dir, filename)
            
            try:
                # Get file info
                file_size = default_storage.size(file_path)
                modified_time = default_storage.get_modified_time(file_path)
                url = default_storage.url(file_path) if hasattr(default_storage, 'url') else f"/media/{file_path}"
                
                # Determine file type
                ext = os.path.splitext(filename)[1].lower()
                is_image = ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
                
                files.append({
                    'filename': filename,
                    'path': file_path,
                    'url': url,
                    'size': file_size,
                    'size_kb': round(file_size / 1024, 1),
                    'modified': modified_time,
                    'is_image': is_image,
                    'is_map': False,
                    'has_tiles': False,
                    'extension': ext
                })
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Also check for maps in the maps subdirectory
        maps_dir = 'site_assets/maps/'
        if default_storage.exists(maps_dir):
            try:
                map_directories, map_filenames = default_storage.listdir(maps_dir)
                
                for filename in map_filenames:
                    # Skip metadata files and anything that's not an image
                    if filename == 'metadata.json':
                        continue
                    
                    file_path = _storage_join(maps_dir, filename)
                    
                    # Skip if it's actually a directory (shouldn't happen but be safe)
                    ext = os.path.splitext(filename)[1].lower()
                    if not ext or ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                        continue
                    
                    try:
                        # Get file info
                        file_size = default_storage.size(file_path)
                        modified_time = default_storage.get_modified_time(file_path)
                        url = default_storage.url(file_path) if hasattr(default_storage, 'url') else f"/media/{file_path}"
                        
                        # Check if tiles exist
                        base_name = os.path.splitext(filename)[0]
                        tiles_path = _storage_join('site_assets/maps', f'{base_name}_tiles')
                        has_tiles = default_storage.exists(_storage_join(tiles_path, 'metadata.json'))
                        
                        files.append({
                            'filename': filename,
                            'path': file_path,
                            'url': url,
                            'size': file_size,
                            'size_kb': round(file_size / 1024, 1),
                            'size_mb': round(file_size / (1024 * 1024), 1),
                            'modified': modified_time,
                            'is_image': True,
                            'is_map': True,
                            'has_tiles': has_tiles,
                            'map_name': base_name,
                            'extension': ext
                        })
                    except Exception as e:
                        # Skip files that can't be read
                        continue
            except Exception as e:
                # Maps directory might not exist or be inaccessible
                pass
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
    except Exception as e:
        # Directory might not exist yet
        pass
    
    return render(request, 'website/manage_assets.html', {'files': files})

@staff_member_required
@require_http_methods(["DELETE", "POST"])
@csrf_protect
def delete_site_asset(request):
    """Delete a site asset file."""
    try:
        if request.method == "POST":
            # Handle POST request with filename in body
            data = json.loads(request.body)
            filename = data.get('filename')
        else:
            # Handle DELETE request
            data = json.loads(request.body)
            filename = data.get('filename')
        
        if not filename:
            return JsonResponse({'error': 'No filename provided'}, status=400)
        
        # Security check - sanitize filename
        filename = os.path.basename(filename)
        
        # Check if file is in regular site_assets or maps subdirectory
        file_path = _storage_join('site_assets', filename)
        map_file_path = _storage_join('site_assets/maps', filename)
        
        # Determine which path exists
        if default_storage.exists(file_path):
            target_path = file_path
            is_map = False
        elif default_storage.exists(map_file_path):
            target_path = map_file_path
            is_map = True
        else:
            return JsonResponse({'error': 'File not found'}, status=404)
        
        # Security check - ensure path is safe
        if not target_path.startswith('site_assets/'):
            return JsonResponse({'error': 'Invalid file path'}, status=400)
        
        # Delete the file
        default_storage.delete(target_path)
        
        # If it's a map, also delete associated tiles
        if is_map:
            base_name = os.path.splitext(filename)[0]
            tiles_path = _storage_join('site_assets/maps', f'{base_name}_tiles')
            # Delete tiles directory (handles non-existent paths gracefully)
            _delete_storage_tree(tiles_path)
        
        return JsonResponse({
            'success': True,
            'message': f'File {filename} deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_POST
@csrf_protect
def rename_site_asset(request):
    """Rename a site asset file."""
    try:
        data = json.loads(request.body)
        old_filename = data.get('old_filename')
        new_filename = data.get('new_filename')
        
        if not old_filename or not new_filename:
            return JsonResponse({'error': 'Both old and new filenames required'}, status=400)
        
        # Sanitize filenames (remove path separators and special chars)
        old_filename = os.path.basename(old_filename)
        new_filename = os.path.basename(new_filename)
        new_filename = new_filename.replace('..', '')
        
        if not new_filename:
            return JsonResponse({'error': 'Invalid new filename'}, status=400)
        
        # Check if file is in regular site_assets or maps subdirectory
        old_regular_path = _storage_join('site_assets', old_filename)
        old_map_path = _storage_join('site_assets/maps', old_filename)
        
        # Determine which path exists
        if default_storage.exists(old_regular_path):
            old_file_path = old_regular_path
            new_file_path = _storage_join('site_assets', new_filename)
            is_map = False
        elif default_storage.exists(old_map_path):
            old_file_path = old_map_path
            new_file_path = _storage_join('site_assets/maps', new_filename)
            is_map = True
        else:
            return JsonResponse({'error': 'Original file not found'}, status=404)
        
        # Security check - ensure paths are safe
        if not old_file_path.startswith('site_assets/') or not new_file_path.startswith('site_assets/'):
            return JsonResponse({'error': 'Invalid file path'}, status=400)
        
        # Check if new filename already exists
        if default_storage.exists(new_file_path):
            return JsonResponse({'error': f'File {new_filename} already exists'}, status=400)
        
        # Read the old file content
        with default_storage.open(old_file_path, 'rb') as old_file:
            file_content = old_file.read()
        
        # Write to new location
        default_storage.save(new_file_path, ContentFile(file_content))
        
        # Delete old file
        default_storage.delete(old_file_path)

        # If it's a map, rename associated tiles directory
        if is_map:
            old_base = os.path.splitext(old_filename)[0]
            new_base = os.path.splitext(new_filename)[0]
            old_tiles_path = _storage_join('site_assets/maps', f'{old_base}_tiles')
            new_tiles_path = _storage_join('site_assets/maps', f'{new_base}_tiles')
            if default_storage.exists(old_tiles_path):
                try:
                    old_tiles_fs = default_storage.path(old_tiles_path)
                    new_tiles_fs = default_storage.path(new_tiles_path)
                    shutil.move(old_tiles_fs, new_tiles_fs)
                except (NotImplementedError, AttributeError):
                    _rename_storage_tree(old_tiles_path, new_tiles_path)

            metadata_path = _storage_join(new_tiles_path, 'metadata.json')
            if default_storage.exists(metadata_path):
                try:
                    with default_storage.open(metadata_path, 'r') as meta_file:
                        metadata = json.load(meta_file)
                    metadata['tiles_path'] = new_tiles_path
                    with default_storage.open(metadata_path, 'w') as meta_file:
                        json.dump(metadata, meta_file)
                except Exception:
                    pass
        
        # Get new URL
        new_url = default_storage.url(new_file_path) if hasattr(default_storage, 'url') else f"/media/{new_file_path}"
        
        return JsonResponse({
            'success': True,
            'message': f'File renamed from {old_filename} to {new_filename}',
            'new_filename': new_filename,
            'new_url': new_url
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==================== MAP TILING FUNCTIONS ====================

def generate_map_tiles(map_filename, max_zoom=5):
    """
    Generate map tiles from a high-resolution map image using PIL.
    Creates a pyramid of tiles at different zoom levels.
    
    Args:
        map_filename: The filename of the map in site_assets/maps/
        max_zoom: Maximum zoom level (default 5 = 6 levels from 0-5)
    
    Returns:
        dict with success status and tile info
    """
    try:
        # Load the original map
        map_path = f"site_assets/maps/{map_filename}"
        if not default_storage.exists(map_path):
            return {'success': False, 'error': 'Map file not found'}

        # Prepare local paths for processing
        # default_storage may be remote; use local temporary files if needed
        base_name = os.path.splitext(map_filename)[0]
        tiles_base_path = _storage_join('site_assets/maps', f'{base_name}_tiles')

        # Clean existing tile directory before regeneration
        if default_storage.exists(tiles_base_path):
            # If storage is local filesystem, delete directory recursively
            try:
                storage_path = default_storage.path(tiles_base_path)
                shutil.rmtree(storage_path, ignore_errors=True)
            except NotImplementedError:
                # fallback: walk files via listdir and delete individually
                _delete_storage_tree(tiles_base_path)

        with default_storage.open(map_path, 'rb') as f:
            img = Image.open(f)
            img.load()  # Force load the image data

        original_width, original_height = img.size

        # Tile size (standard is 256x256)
        tile_size = 256

        # Calculate dimensions at max zoom
        # At max zoom, we want the full resolution (or close to it)
        max_zoom_width = original_width
        max_zoom_height = original_height

        # Make dimensions multiples of tile_size for cleaner tiling
        max_zoom_width = math.ceil(max_zoom_width / tile_size) * tile_size
        max_zoom_height = math.ceil(max_zoom_height / tile_size) * tile_size

        tile_count = 0

        zoom_levels = []

        # Generate tiles for each zoom level (Leaflet standard: 0 = zoomed out, higher = zoomed in)
        for zoom in range(max_zoom + 1):
            # Calculate size for this zoom level
            # zoom 0 = smallest (most zoomed out), zoom 5 = largest (most zoomed in/full res)
            # At zoom 0, scale_factor = 32 (1/32 size)
            # At zoom 5, scale_factor = 1 (full size)
            scale_factor = 2 ** (max_zoom - zoom)
            zoom_width = max(tile_size, max_zoom_width // scale_factor)
            zoom_height = max(tile_size, max_zoom_height // scale_factor)

            # Resize image for this zoom level
            resized_img = img.resize((zoom_width, zoom_height), Image.LANCZOS)

            # Calculate number of tiles needed
            tiles_x = math.ceil(zoom_width / tile_size)
            tiles_y = math.ceil(zoom_height / tile_size)

            zoom_levels.append({
                'zoom': zoom,
                'width': zoom_width,
                'height': zoom_height,
                'tiles_x': tiles_x,
                'tiles_y': tiles_y
            })

            # Create tiles for this zoom level
            for x in range(tiles_x):
                for y in range(tiles_y):
                    # Extract tile
                    left = x * tile_size
                    top = y * tile_size
                    right = min(left + tile_size, zoom_width)
                    bottom = min(top + tile_size, zoom_height)

                    tile = resized_img.crop((left, top, right, bottom))

                    # If tile is smaller than tile_size, pad it
                    if tile.size != (tile_size, tile_size):
                        # Ensure we use the correct mode for the padded image
                        mode = tile.mode if tile.mode in ['RGBA', 'RGB', 'L'] else 'RGBA'
                        if mode == 'RGBA':
                            padded = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
                        else:
                            padded = Image.new('RGB', (tile_size, tile_size), (0, 0, 0))
                        padded.paste(tile, (0, 0))
                        tile = padded

                    # Save tile
                    tile_path = _storage_join(tiles_base_path, str(zoom), str(x), f'{y}.png')

                    # Ensure directory exists
                    _storage_makedirs(os.path.dirname(tile_path))

                    # Convert to bytes
                    buffer = io.BytesIO()
                    tile.save(buffer, format='PNG', optimize=True)
                    buffer.seek(0)

                    # Save to storage (overwrite existing)
                    with default_storage.open(tile_path, 'wb') as tile_file:
                        tile_file.write(buffer.read())
                    tile_count += 1

        # Save metadata
        metadata = {
            'original_width': original_width,
            'original_height': original_height,
            'max_zoom': max_zoom,
            'tile_size': tile_size,
            'tile_count': tile_count,
            'tiles_path': tiles_base_path,
            'max_zoom_width': max_zoom_width,
            'max_zoom_height': max_zoom_height,
            'zoom_levels': zoom_levels
        }

        metadata_path = _storage_join(tiles_base_path, 'metadata.json')
        with default_storage.open(metadata_path, 'w') as meta_file:
            json.dump(metadata, meta_file)

        return {
            'success': True,
            'tile_count': tile_count,
            'metadata': metadata,
            'tiles_path': tiles_base_path
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


@staff_member_required
@require_POST
@csrf_protect
def tile_map(request):
    """
    Endpoint to generate tiles for a map.
    Accepts the map filename and generates all necessary tiles.
    """
    try:
        data = json.loads(request.body)
        map_filename = data.get('filename')
        max_zoom = data.get('max_zoom', 5)  # Default to 5 zoom levels
        
        if not map_filename:
            return JsonResponse({'error': 'No filename provided'}, status=400)
        
        # Security check - ensure filename is just a filename, not a path
        map_filename = os.path.basename(map_filename)
        
        # Generate tiles
        result = generate_map_tiles(map_filename, max_zoom)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f"Generated {result['tile_count']} tiles successfully",
                'tile_count': result['tile_count'],
                'tiles_path': result['tiles_path'],
                'metadata': result['metadata']
            })
        else:
            return JsonResponse({'error': result['error']}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def view_map(request, map_name):
    """
    View to display an interactive map using Leaflet.js
    """
    # Security check - sanitize map name
    map_name = os.path.basename(map_name)
    
    # Check if tiles exist
    tiles_path = _storage_join('site_assets/maps', f'{map_name}_tiles')
    metadata_path = _storage_join(tiles_path, 'metadata.json')
    
    if not default_storage.exists(metadata_path):
        return render(request, 'website/map_error.html', {
            'error': 'Map tiles not found. Please generate tiles first.',
            'map_name': map_name
        })
    
    # Load metadata
    with default_storage.open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Get base URL for tiles
    if hasattr(default_storage, 'url'):
        tiles_base_url = default_storage.url(tiles_path)
    else:
        tiles_base_url = f"/media/{tiles_path}"
    
    # Calculate center coordinates
    center_y = metadata['original_height'] / 2
    center_x = metadata['original_width'] / 2
    
    tile_size = metadata.get('tile_size', 256)
    max_zoom = metadata['max_zoom']
    max_zoom_width = metadata.get('max_zoom_width')
    max_zoom_height = metadata.get('max_zoom_height')

    if not max_zoom_width or not max_zoom_height:
        max_zoom_width = math.ceil(metadata['original_width'] / tile_size) * tile_size
        max_zoom_height = math.ceil(metadata['original_height'] / tile_size) * tile_size

    zoom_levels = metadata.get('zoom_levels', [])

    # Load map locations from database
    from web.worldinfo.models import MapLocation
    locations = MapLocation.objects.filter(map_name=map_name).values(
        'id', 'name', 'description', 'location_type', 'x_coord', 'y_coord', 'link_url'
    )
    
    context = {
        'map_name': map_name,
        'tiles_base_url': tiles_base_url,
        'metadata': metadata,
        'max_zoom': max_zoom,
        'tile_size': tile_size,
        'original_width': metadata['original_width'],
        'original_height': metadata['original_height'],
        'max_zoom_width': max_zoom_width,
        'max_zoom_height': max_zoom_height,
        'center_y': center_y,
        'center_x': center_x,
        'zoom_levels_json': json.dumps(zoom_levels),
        'locations_json': json.dumps(list(locations)),
        'is_staff': request.user.is_staff if request.user.is_authenticated else False
    }
    
    return render(request, 'website/map_viewer.html', context)


# ==================== MAP LOCATION MANAGEMENT ====================

@staff_member_required
@require_POST
@csrf_protect
def create_map_location(request):
    """Create a new map location."""
    try:
        from web.worldinfo.models import MapLocation
        
        data = json.loads(request.body)
        location = MapLocation.objects.create(
            map_name=data.get('map_name'),
            name=data.get('name'),
            description=data.get('description', ''),
            location_type=data.get('location_type', 'other'),
            x_coord=data.get('x_coord'),
            y_coord=data.get('y_coord'),
            link_url=data.get('link_url', '')
        )
        
        return JsonResponse({
            'success': True,
            'location': {
                'id': location.id,
                'name': location.name,
                'description': location.description,
                'location_type': location.location_type,
                'x_coord': location.x_coord,
                'y_coord': location.y_coord,
                'link_url': location.link_url
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_POST
@csrf_protect
def update_map_location(request, location_id):
    """Update an existing map location."""
    try:
        from web.worldinfo.models import MapLocation
        
        location = MapLocation.objects.get(id=location_id)
        data = json.loads(request.body)
        
        location.name = data.get('name', location.name)
        location.description = data.get('description', location.description)
        location.location_type = data.get('location_type', location.location_type)
        location.x_coord = data.get('x_coord', location.x_coord)
        location.y_coord = data.get('y_coord', location.y_coord)
        location.link_url = data.get('link_url', location.link_url)
        location.save()
        
        return JsonResponse({
            'success': True,
            'location': {
                'id': location.id,
                'name': location.name,
                'description': location.description,
                'location_type': location.location_type,
                'x_coord': location.x_coord,
                'y_coord': location.y_coord,
                'link_url': location.link_url
            }
        })
    except MapLocation.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@require_POST
@csrf_protect
def delete_map_location(request, location_id):
    """Delete a map location."""
    try:
        from web.worldinfo.models import MapLocation
        
        location = MapLocation.objects.get(id=location_id)
        location.delete()
        
        return JsonResponse({'success': True})
    except MapLocation.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
