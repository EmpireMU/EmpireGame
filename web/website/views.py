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

@staff_member_required
def upload_site_asset(request):
    if request.method == 'POST':
        if 'asset' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        asset_file = request.FILES['asset']
        asset_type = request.POST.get('type', 'logo')  # logo, icon, etc.
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        ext = os.path.splitext(asset_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'error': 'Invalid file type'}, status=400)
        
        # Save to site_assets directory
        filename = f"{asset_type}_{uuid.uuid4()}{ext}"
        path = f"site_assets/{filename}"
        saved_path = default_storage.save(path, asset_file)
        
        url = default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}"
        
        return JsonResponse({
            'success': True,
            'filename': filename,
            'url': url,
            'path': saved_path
        })
    
    return render(request, 'website/upload_assets.html')
