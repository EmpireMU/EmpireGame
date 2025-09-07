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
        
        # Use custom name if provided, otherwise use type + UUID
        if custom_name:
            filename = f"{custom_name}.jpg"  # Force JPG for consistency
        else:
            filename = f"{asset_type}_{uuid.uuid4()}.jpg"
        
        # Resize and compress the image (800px max, good quality)
        try:
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
