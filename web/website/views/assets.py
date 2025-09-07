# Simple site assets upload for admins
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os

# Import resize function from roster
from web.roster.views import resize_image
from PIL import Image, ImageOps
from PIL.Image import LANCZOS
import io

def resize_image_with_transparency(image_file, max_size):
    """Resize image while preserving transparency for logos/icons/emblems."""
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
        asset_type = request.POST.get('type', 'logo')  # logo, icon, etc.
        custom_name = request.POST.get('custom_name', '')  # Optional custom filename
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        ext = os.path.splitext(asset_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'error': 'Invalid file type'}, status=400)
        
        # Determine if we should preserve transparency
        preserve_transparency = asset_type in ['logo', 'icon', 'emblem']
        
        # Use custom name if provided, otherwise use type + UUID
        if custom_name:
            filename = f"{custom_name}.png" if preserve_transparency else f"{custom_name}.jpg"
        else:
            filename = f"{asset_type}_{uuid.uuid4()}.png" if preserve_transparency else f"{asset_type}_{uuid.uuid4()}.jpg"
        
        # Resize the image (800px max)
        try:
            if preserve_transparency:
                # For logos/icons/emblems, preserve transparency
                compressed_buffer = resize_image_with_transparency(asset_file, 800)
            else:
                # For other assets, use white background like character images
                compressed_buffer = resize_image(asset_file, 800, good_quality=True)
            
            path = f"site_assets/{filename}"
            saved_path = default_storage.save(path, ContentFile(compressed_buffer.read()))
        except Exception as e:
            return JsonResponse({'error': f'Could not process image: {e}'}, status=400)
        
        url = default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}"
        
        return JsonResponse({
            'success': True,
            'filename': filename,
            'url': url,
            'path': saved_path
        })
    
    return render(request, 'website/upload_assets.html')
