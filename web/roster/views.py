from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
import os
import uuid
import io
from PIL import Image

# Handle different Pillow versions
try:
    from PIL.Image import Resampling
    LANCZOS = Resampling.LANCZOS
except ImportError:
    # Older Pillow versions
    LANCZOS = Image.LANCZOS
from evennia.objects.models import ObjectDB
from typeclasses.characters import STATUS_UNFINISHED, STATUS_AVAILABLE, STATUS_ACTIVE, STATUS_GONE
from typeclasses.organisations import Organisation
import logging

logger = logging.getLogger('web')

def is_staff_user(user):
    """
    Check if a user has staff privileges (either Django staff or Evennia Admin/Builder).
    
    Args:
        user: Django User object
        
    Returns:
        bool: True if user has staff privileges
    """
    # Anonymous users are not staff
    if not user.is_authenticated:
        return False
    
    return user.is_staff or user.check_permstring("Admin") or user.check_permstring("Builder")

def get_character_images(character):
    """
    Get all images for a character from their image_gallery attribute.
    Returns a list of dictionaries with image info.
    """
    gallery = character.attributes.get('image_gallery', default=[], category='gallery')
    return gallery

def validate_image_upload(image_file):
    """
    Check if uploaded file is a reasonable image before processing.
    Catches edge cases early.
    """
    # Check file size (reject if over 15MB - bigger than any reasonable character image)
    if image_file.size > 15 * 1024 * 1024:
        raise ValueError("Image too large (max 15MB)")
    
    # Check if it's actually an image
    try:
        img = Image.open(image_file)
        img.verify()
        image_file.seek(0)  # Reset for later use
    except Exception:
        raise ValueError("File is not a valid image")
    
    return True

def resize_image(image_file, max_size, good_quality=True):
    """Simple resize. That's it."""
    img = Image.open(image_file)
    
    # Handle transparency properly - use white background instead of black
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create a white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize it
    img.thumbnail((max_size, max_size), LANCZOS)
    
    # Save it
    buffer = io.BytesIO()
    quality = 85 if good_quality else 75
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    buffer.seek(0)
    return buffer

def save_character_image(character, image_file, caption=""):
    """
    Save an uploaded image to the character's gallery.
    Creates full-size image (800px) and thumbnail (150px).
    Returns the image info dictionary.
    """
    # Validate upload first - catch problems early
    validate_image_upload(image_file)
    
    char_dir = f"character_images/{character.id}"
    image_id = str(uuid.uuid4())
    
    try:
        # Create full-size image (800px, good quality)
        full_buffer = resize_image(image_file, 800, good_quality=True)
        full_filename = f"{image_id}_full.jpg"
        full_path = f"{char_dir}/{full_filename}"
        full_saved = default_storage.save(full_path, ContentFile(full_buffer.read()))
        
        # Create thumbnail (150px, lower quality for smaller size)
        image_file.seek(0)
        thumb_buffer = resize_image(image_file, 150, good_quality=False)
        thumb_filename = f"{image_id}_thumb.jpg"
        thumb_path = f"{char_dir}/{thumb_filename}"
        thumb_saved = default_storage.save(thumb_path, ContentFile(thumb_buffer.read()))
        
    except Exception as e:
        logger.error(f"Error saving character image: {e}")
        raise ValueError(f"Could not save image: {e}")
    
    # Create image info
    image_info = {
        'id': image_id,
        'filename': full_filename,
        'path': full_saved,
        'thumbnail_path': thumb_saved,
        'caption': caption,
        'url': default_storage.url(full_saved) if hasattr(default_storage, 'url') else f"/media/{full_saved}",
        'thumbnail_url': default_storage.url(thumb_saved) if hasattr(default_storage, 'url') else f"/media/{thumb_saved}",
        'uploaded_at': str(timezone.now())
    }
    
    # Add to character's gallery
    gallery = character.attributes.get('image_gallery', default=[], category='gallery')
    gallery.append(image_info)
    character.attributes.add('image_gallery', gallery, category='gallery')
    
    return image_info

def remove_character_image(character, image_id):
    """
    Delete an image from the character's gallery.
    Removes both full-size image and thumbnail.
    """
    gallery = character.attributes.get('image_gallery', default=[], category='gallery')
    
    # Find and remove the image
    for i, img in enumerate(gallery):
        if img.get('id') == image_id:
            # Delete the full-size image file
            try:
                if default_storage.exists(img['path']):
                    default_storage.delete(img['path'])
            except Exception as e:
                logger.warning(f"Could not delete full-size image file {img['path']}: {e}")
            
            # Delete the thumbnail file if it exists
            try:
                if 'thumbnail_path' in img and default_storage.exists(img['thumbnail_path']):
                    default_storage.delete(img['thumbnail_path'])
            except Exception as e:
                logger.warning(f"Could not delete thumbnail file {img.get('thumbnail_path', 'unknown')}: {e}")
            
            # Remove from gallery
            gallery.pop(i)
            character.attributes.add('image_gallery', gallery, category='gallery')
            return True
    
    return False

def roster_view(request):
    """
    Main view for the character roster.
    Shows available, active, and retired characters.
    Staff can also see unfinished characters.
    """
    # Check if user is staff (either Django staff or Evennia Admin/Builder)
    is_staff = is_staff_user(request.user)
    
    # Get characters by status (with attributes pre-loaded)
    available_chars = ObjectDB.objects.filter(db_attributes__db_key='status', 
                                           db_attributes__db_value=STATUS_AVAILABLE).prefetch_related('db_attributes').order_by('db_key')
    active_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                        db_attributes__db_value=STATUS_ACTIVE).prefetch_related('db_attributes').order_by('db_key')
    gone_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                      db_attributes__db_value=STATUS_GONE).prefetch_related('db_attributes').order_by('db_key')
    
    # Get unfinished characters (only if user is staff)
    unfinished_chars = []
    if is_staff:
        unfinished_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                                db_attributes__db_value=STATUS_UNFINISHED).prefetch_related('db_attributes').order_by('db_key')
    
    # Filter out staff accounts
    available_chars = [char for char in available_chars if not (char.account and char.account.check_permstring("Builder"))]
    active_chars = [char for char in active_chars if not (char.account and char.account.check_permstring("Builder"))]
    gone_chars = [char for char in gone_chars if not (char.account and char.account.check_permstring("Builder"))]
    
    # Filter unfinished characters too (only if we have them)
    if is_staff:
        unfinished_chars = [char for char in unfinished_chars if not (char.account and char.account.check_permstring("Builder"))]
    
    # Get all organizations
    organizations = ObjectDB.objects.filter(db_typeclass_path='typeclasses.organisations.Organisation').order_by('db_key')
    
    # Helper function to get concept
    def get_concept(char):
        try:
            if hasattr(char, 'distinctions'):
                concept = char.distinctions.get("concept")
                if concept:
                    return concept.name
        except Exception:
            pass
        return "No concept set"

    # Helper function to get display name
    def get_display_name(char):
        return char.db.full_name or char.name

    # Build organization data efficiently - loop through characters once
    org_data = {status: [] for status in ['available', 'active', 'gone']}
    if is_staff:
        org_data['unfinished'] = []
    
    # Create org buckets for each status
    org_buckets = {}
    for status in org_data.keys():
        org_buckets[status] = {}
        for org in organizations:
            org_buckets[status][org.id] = []
    
    # Process all character lists once
    status_lists = [('available', available_chars), 
                   ('active', active_chars), 
                   ('gone', gone_chars)]
    if is_staff:
        status_lists.append(('unfinished', unfinished_chars))
    
    for status, char_list in status_lists:
        for char in char_list:
            try:
                # Get character's organizations once
                char_orgs = char.attributes.get('organisations', default={}, category='organisations')
                
                for org_id, rank in char_orgs.items():
                    if org_id in org_buckets[status]:
                        # Find the org object for rank names
                        org = next((o for o in organizations if o.id == org_id), None)
                        if org:
                            rank_name = org.db.rank_names.get(rank, f"Rank {rank}")
                            char_data = (char, get_concept(char), get_display_name(char), rank_name)
                            org_buckets[status][org_id].append((char_data, rank))
            except Exception:
                continue
    
    # Sort and format the organization data
    for status in org_data.keys():
        status_orgs = []
        for org in organizations:
            if org_buckets[status][org.id]:
                # Sort by rank then name
                sorted_chars = sorted(org_buckets[status][org.id], key=lambda x: (x[1], x[0][0].key.lower()))
                char_tuples = [char_data for char_data, rank in sorted_chars]
                status_orgs.append((org, char_tuples))
        org_data[status] = status_orgs

    # Prepare context with character data
    context = {
        'available_chars': [(char, get_concept(char), get_display_name(char)) for char in available_chars],
        'active_chars': [(char, get_concept(char), get_display_name(char)) for char in active_chars],
        'gone_chars': [(char, get_concept(char), get_display_name(char)) for char in gone_chars],
        'organizations': org_data,
        'is_staff': is_staff
    }
    
    # Add unfinished characters if user is staff
    if is_staff:
        context['unfinished_chars'] = [(char, get_concept(char), get_display_name(char)) for char in unfinished_chars]
    
    return render(request, 'roster/roster.html', context)

def character_detail_view(request, char_name, char_id):
    """
    Detailed view for a specific character.
    Shows character's biography, traits, and other information.
    """
    # Get the character or 404
    character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
    
    # Check if user can see traits (staff or character owner)
    # Since account names match character names, check username against character name
    can_see_traits = is_staff_user(request.user) or (request.user.username.lower() == character.name.lower())
    
    # Get character's basic info
    basic_info = {
        'name': character.db.full_name or character.name,
        'concept': character.distinctions.get('concept').name if character.distinctions.get('concept') else None,
        'gender': character.db.gender,
        'age': character.db.age,
        'birthday': character.db.birthday,
        'realm': character.db.realm,
        'culture': character.distinctions.get('culture').name if character.distinctions.get('culture') else None,
        'vocation': character.distinctions.get('vocation').name if character.distinctions.get('vocation') else None,
        'notable_traits': character.db.notable_traits,
        'description': character.db.desc,
        'background': character.db.background,
        'personality': character.db.personality,
        'special_effects': character.db.special_effects,
        'secret_information': character.db.secret_information,
    }
    
    # Get character's organizations
    organizations = []
    for org_id, rank in character.organisations.items():
        try:
            org = ObjectDB.objects.get(id=org_id)
            rank_name = org.db.rank_names.get(rank, f"Rank {rank}")
            organizations.append({
                'name': org.name,
                'rank': rank_name
            })
        except ObjectDB.DoesNotExist:
            continue
    
    # Get character's image gallery
    gallery_images = get_character_images(character)
    
    # Get character's family relationships
    from web.relationships.views import get_character_family
    family_relationships = get_character_family(character.id)
    
    context = {
        'character': character,
        'basic_info': basic_info,
        'organizations': organizations,
        'can_see_traits': can_see_traits,
        'gallery_images': gallery_images,
        'family_relationships': family_relationships,
        'is_staff': is_staff_user(request.user),
    }
    
    # Only include traits if user has permission
    if can_see_traits:
        # Get character's distinctions
        distinctions = {}
        for key in character.distinctions.all():
            trait = character.distinctions.get(key)
            distinctions[trait.name or key] = {
                'key': key,
                'value': f"d{int(trait.value)}"
            }
        
        # Get character's attributes
        attributes = {}
        for key in character.character_attributes.all():
            trait = character.character_attributes.get(key)
            attributes[trait.name or key] = {
                'key': key,
                'value': f"d{int(trait.value)}"
            }
        
        # Get character's skills
        skills = {}
        for key in character.skills.all():
            trait = character.skills.get(key)
            skills[trait.name or key] = {
                'key': key,
                'value': f"d{int(trait.value)}"
            }
        
        # Get character's signature assets
        signature_assets = {}
        for key in character.signature_assets.all():
            trait = character.signature_assets.get(key)
            signature_assets[key] = {
                'key': key,
                'description': trait.desc or "No description",
                'value': f"d{int(trait.value)}"
            }
        
        # Add traits to context
        context.update({
            'distinctions': distinctions,
            'attributes': attributes,
            'skills': skills,
            'signature_assets': signature_assets,
        })
    
    return render(request, 'roster/character_detail.html', context)

@require_POST
@csrf_protect
def update_character_field(request, char_name, char_id):
    """
    API endpoint to update a character field.
    Only accessible by staff members.
    """
    try:
        if not is_staff_user(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
        field = request.POST.get('field')
        value = request.POST.get('value', '')
        
        if not field:
            return JsonResponse({'error': 'Missing field'}, status=400)
        
        # Handle distinction updates (special case for freeform text)
        if field.startswith('distinction_'):
            # Format: distinction_<slot>_<field> where field is 'name' or 'description'
            try:
                _, slot, field_type = field.split('_', 2)
                
                # Validate slot
                valid_slots = ['concept', 'culture', 'vocation']
                if slot not in valid_slots:
                    return JsonResponse({'error': f'Invalid distinction slot: {slot}'}, status=400)
                
                # Validate field type
                if field_type not in ['name', 'description']:
                    return JsonResponse({'error': f'Invalid distinction field: {field_type}'}, status=400)
                
                # Get the current distinction if it exists
                distinction = character.distinctions.get(slot)
                
                if field_type == 'name':
                    # Update the name - need to preserve existing description
                    current_desc = distinction.desc if distinction else "No description"
                    # Use the same method as setdist command
                    character.distinctions.add(slot, value or "Unnamed", trait_type="static", base=8, desc=current_desc)
                elif field_type == 'description':
                    # Update the description - need to preserve existing name
                    current_name = distinction.name if distinction else "Unnamed"
                    # Use the same method as setdist command
                    character.distinctions.add(slot, current_name, trait_type="static", base=8, desc=value or "No description")
                
                logger.info(f"Updated {char_name}'s {slot} distinction {field_type} to: {value}")
                
                return JsonResponse({
                    'success': True,
                    'value': value,
                    'message': f'Successfully updated {slot} {field_type}'
                })
                
            except ValueError:
                return JsonResponse({'error': 'Invalid distinction field format'}, status=400)
        
        # Handle trait updates
        if field.startswith('trait_'):
            # Format: trait_<category>_<trait_key>
            try:
                _, category, trait_key = field.split('_', 2)
                
                # Validate die size
                if not value.startswith('d') or not value[1:].isdigit():
                    return JsonResponse({'error': 'Die size must be in format dN (e.g., d4, d6, d8, d10, d12)'}, status=400)
                
                die_size = int(value[1:])
                if die_size not in [4, 6, 8, 10, 12]:
                    return JsonResponse({'error': 'Die size must be one of: d4, d6, d8, d10, d12'}, status=400)
                
                # Get the appropriate trait handler
                if category == 'attributes':
                    handler = character.character_attributes
                elif category == 'skills':
                    handler = character.skills
                elif category == 'distinctions':
                    handler = character.distinctions
                elif category == 'signature_assets':
                    handler = character.signature_assets
                elif category == 'powers':
                    handler = character.powers
                else:
                    return JsonResponse({'error': f'Invalid trait category: {category}'}, status=400)
                
                # Get the trait and update its value
                trait = handler.get(trait_key)
                if not trait:
                    return JsonResponse({'error': f'Trait not found: {trait_key}'}, status=400)
                
                # Update the trait value
                trait.base = die_size
                
                logger.info(f"Updated {char_name}'s {category} {trait_key} to d{die_size}")
                
                return JsonResponse({
                    'success': True,
                    'value': f'd{die_size}',
                    'message': f'Successfully updated {trait.name or trait_key} to d{die_size}'
                })
                
            except ValueError:
                return JsonResponse({'error': 'Invalid trait field format'}, status=400)
        
        # List of allowed regular fields for editing
        allowed_fields = [
            'full_name',
            'gender',
            'age',
            'birthday',
            'realm',
            'desc',
            'background',
            'personality',
            'notable_traits',
            'special_effects',
            'secret_information'
        ]
        
        if field not in allowed_fields:
            return JsonResponse({'error': f'Invalid field: {field}'}, status=400)
        
        # For character descriptions, normalize line breaks:
        # Convert Evennia line break codes (|/ and |\) to standard newlines
        # so they work consistently in-game and on web
        if field == 'desc' and value:
            value = value.replace('|/', '\n').replace('|\\', '\n')
        
        # Update the field using Evennia's db handler
        setattr(character.db, field, value)
        logger.info(f"Updated {char_name}'s {field}")
        
        return JsonResponse({
            'success': True,
            'value': value,
            'message': f'Successfully updated {field}'
        })
        
    except Exception as e:
        logger.error(f"Error updating character field: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'Server error occurred'
        }, status=500)

@require_POST
@csrf_protect
def upload_character_image(request, char_name, char_id):
    """
    API endpoint to upload an image to a character's gallery.
    Only accessible by staff members or the character owner.
    """
    try:
        character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
        
        # Check permissions (staff or character owner)
        can_edit = is_staff_user(request.user) or (request.user.username.lower() == character.name.lower())
        if not can_edit:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image file provided'}, status=400)
        
        image_file = request.FILES['image']
        caption = request.POST.get('caption', '')
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'error': 'Invalid file type. Allowed: JPG, PNG, GIF, WebP'}, status=400)
        
        # Use our new validation function (handles up to 15MB)
        try:
            validate_image_upload(image_file)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        
        # Check maximum images limit (20 per character)
        current_gallery = character.attributes.get('image_gallery', default=[], category='gallery')
        if len(current_gallery) >= 20:
            return JsonResponse({'error': 'Maximum of 20 images per character allowed'}, status=400)
        
        # Save the image
        image_info = save_character_image(character, image_file, caption)
        
        logger.info(f"Uploaded image for {char_name}: {image_info['filename']}")
        
        return JsonResponse({
            'success': True,
            'image': image_info,
            'message': 'Image uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error uploading character image: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'Server error occurred'
        }, status=500)

@require_POST
@csrf_protect
def delete_character_image(request, char_name, char_id):
    """
    API endpoint to delete an image from a character's gallery.
    Only accessible by staff members or the character owner.
    """
    try:
        character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
        
        # Check permissions (staff or character owner)
        can_edit = is_staff_user(request.user) or (request.user.username.lower() == character.name.lower())
        if not can_edit:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        image_id = request.POST.get('image_id')
        if not image_id:
            return JsonResponse({'error': 'No image ID provided'}, status=400)
        
        # Delete the image
        success = remove_character_image(character, image_id)
        
        if success:
            logger.info(f"Deleted image {image_id} for {char_name}")
            return JsonResponse({
                'success': True,
                'message': 'Image deleted successfully'
            })
        else:
            return JsonResponse({'error': 'Image not found'}, status=404)
        
    except Exception as e:
        logger.error(f"Error deleting character image: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'Server error occurred'
        }, status=500)

@require_POST
@csrf_protect
def set_main_character_image(request, char_name, char_id):
    """
    API endpoint to set a gallery image as the main character image.
    Only accessible by staff members or the character owner.
    """
    try:
        character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
        
        # Check permissions (staff or character owner)
        can_edit = is_staff_user(request.user) or (request.user.username.lower() == character.name.lower())
        if not can_edit:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        image_id = request.POST.get('image_id')
        if not image_id:
            return JsonResponse({'error': 'No image ID provided'}, status=400)
        
        # Find the image in the gallery
        gallery = character.attributes.get('image_gallery', default=[], category='gallery')
        selected_image = None
        
        for img in gallery:
            if img.get('id') == image_id:
                selected_image = img
                break
        
        if not selected_image:
            return JsonResponse({'error': 'Image not found in gallery'}, status=404)
        
        # Set the image as the main character image
        character.db.image_url = selected_image['url']
        
        logger.info(f"Set main image for {char_name} to: {selected_image['filename']}")
        
        return JsonResponse({
            'success': True,
            'image_url': selected_image['url'],
            'message': 'Main image updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error setting main character image: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'Server error occurred'
        }, status=500)

@require_POST
@csrf_protect
def set_secondary_character_image(request, char_name, char_id):
    """
    API endpoint to set a gallery image as the secondary character image.
    Only accessible by staff members or the character owner.
    """
    try:
        character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
        
        # Check permissions (staff or character owner)
        can_edit = is_staff_user(request.user) or (request.user.username.lower() == character.name.lower())
        if not can_edit:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        image_id = request.POST.get('image_id')
        if not image_id:
            return JsonResponse({'error': 'No image ID provided'}, status=400)
        
        # Find the image in the gallery
        gallery = character.attributes.get('image_gallery', default=[], category='gallery')
        selected_image = None
        
        for img in gallery:
            if img.get('id') == image_id:
                selected_image = img
                break
        
        if not selected_image:
            return JsonResponse({'error': 'Image not found in gallery'}, status=404)
        
        # Set the image as the secondary character image
        character.db.secondary_image_url = selected_image['url']
        
        logger.info(f"Set secondary image for {char_name} to: {selected_image['filename']}")
        
        return JsonResponse({
            'success': True,
            'image_url': selected_image['url'],
            'message': 'Secondary image updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error setting secondary character image: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'Server error occurred'
        }, status=500)

@require_POST
@csrf_protect
def set_tertiary_character_image(request, char_name, char_id):
    """
    API endpoint to set a gallery image as the tertiary character image.
    Only accessible by staff members or the character owner.
    """
    try:
        character = get_object_or_404(ObjectDB, id=char_id, db_key__iexact=char_name)
        
        # Check permissions (staff or character owner)
        can_edit = is_staff_user(request.user) or (request.user.username.lower() == character.name.lower())
        if not can_edit:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        image_id = request.POST.get('image_id')
        if not image_id:
            return JsonResponse({'error': 'No image ID provided'}, status=400)
        
        # Find the image in the gallery
        gallery = character.attributes.get('image_gallery', default=[], category='gallery')
        selected_image = None
        
        for img in gallery:
            if img.get('id') == image_id:
                selected_image = img
                break
        
        if not selected_image:
            return JsonResponse({'error': 'Image not found in gallery'}, status=404)
        
        # Set the image as the tertiary character image
        character.db.tertiary_image_url = selected_image['url']
        
        logger.info(f"Set tertiary image for {char_name} to: {selected_image['filename']}")
        
        return JsonResponse({
            'success': True,
            'image_url': selected_image['url'],
            'message': 'Tertiary image updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error setting tertiary character image: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'Server error occurred'
        }, status=500)

def character_search_view(request):
    """
    Search characters by name, concept, and descriptive text.
    Standalone search functionality that doesn't interfere with existing roster.
    """
    query = request.GET.get('q', '').strip()
    results = []
    
    if query and len(query) >= 2:  # Minimum 2 characters to search
        # Check if user is staff (same pattern as roster_view)
        is_staff = is_staff_user(request.user)
        
        # Get characters by status (same pattern as roster_view)
        available_chars = ObjectDB.objects.filter(db_attributes__db_key='status', 
                                               db_attributes__db_value=STATUS_AVAILABLE).prefetch_related('db_attributes')
        active_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                            db_attributes__db_value=STATUS_ACTIVE).prefetch_related('db_attributes')
        gone_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                          db_attributes__db_value=STATUS_GONE).prefetch_related('db_attributes')
        
        # Get unfinished characters (only if user is staff, same as roster_view)
        unfinished_chars = []
        if is_staff:
            unfinished_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                                    db_attributes__db_value=STATUS_UNFINISHED).prefetch_related('db_attributes')
        
        # Combine all character lists
        all_chars = list(available_chars) + list(active_chars) + list(gone_chars)
        if is_staff:
            all_chars.extend(list(unfinished_chars))
        
        # Filter out staff accounts (same pattern as roster_view)
        characters = [char for char in all_chars if not (char.account and char.account.check_permstring("Builder"))]
        
        # Search through characters
        query_lower = query.lower()
        
        for char in characters:
            match_score = 0
            matched_fields = []
            
            # Search character name (highest priority)
            if query_lower in char.key.lower():
                match_score += 10
                matched_fields.append('name')
            
            # Search full name
            full_name = char.db.full_name or ""
            if query_lower in full_name.lower():
                match_score += 8
                matched_fields.append('full name')
            
            # Search concept
            try:
                concept = char.distinctions.get("concept")
                if concept and query_lower in concept.name.lower():
                    match_score += 6
                    matched_fields.append('concept')
            except:
                pass
            
            # Search descriptive fields
            descriptive_fields = [
                ('desc', 'description'),
                ('background', 'background'),
                ('personality', 'personality'),
                ('notable_traits', 'notable traits')
            ]
            
            for field_name, display_name in descriptive_fields:
                field_value = getattr(char.db, field_name, "") or ""
                if query_lower in field_value.lower():
                    match_score += 3
                    matched_fields.append(display_name)
            
            # If we found any matches, add to results
            if match_score > 0:
                # Get character status
                status = char.attributes.get('status', 'unknown')
                status_display = {
                    STATUS_AVAILABLE: 'Available',
                    STATUS_ACTIVE: 'Active', 
                    STATUS_GONE: 'Gone',
                    STATUS_UNFINISHED: 'Unfinished'
                }.get(status, 'Unknown')
                
                # Get concept for display
                try:
                    concept = char.distinctions.get("concept")
                    concept_name = concept.name if concept else "No concept set"
                except:
                    concept_name = "No concept set"
                
                # Create a snippet showing relevant matched content
                snippet_parts = []
                if 'description' in matched_fields and char.db.desc:
                    snippet_parts.append(f"Description: {char.db.desc[:100]}...")
                elif 'background' in matched_fields and char.db.background:
                    snippet_parts.append(f"Background: {char.db.background[:100]}...")
                elif 'personality' in matched_fields and char.db.personality:
                    snippet_parts.append(f"Personality: {char.db.personality[:100]}...")
                
                snippet = " | ".join(snippet_parts) if snippet_parts else ""
                
                results.append({
                    'character': char,
                    'name': char.db.full_name or char.key,
                    'concept': concept_name,
                    'status': status_display,
                    'score': match_score,
                    'matched_fields': matched_fields,
                    'snippet': snippet
                })
        
        # Sort results by score (highest first), then by name
        results.sort(key=lambda x: (-x['score'], x['name'].lower()))
    
    context = {
        'query': query,
        'results': results,
        'result_count': len(results),
        'is_staff': is_staff_user(request.user),
    }
    
    return render(request, 'roster/search.html', context)
