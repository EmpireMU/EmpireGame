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
from evennia.objects.models import ObjectDB
from typeclasses.characters import STATUS_AVAILABLE, STATUS_ACTIVE, STATUS_GONE
from typeclasses.organisations import Organisation
import logging

logger = logging.getLogger('web')

def get_character_images(character):
    """
    Get all images for a character from their image_gallery attribute.
    Returns a list of dictionaries with image info.
    """
    gallery = character.attributes.get('image_gallery', default=[], category='gallery')
    return gallery

def save_character_image(character, image_file, caption=""):
    """
    Save an uploaded image to the character's gallery.
    Returns the image info dictionary.
    """
    # Create character images directory if it doesn't exist
    char_dir = f"character_images/{character.id}"
    
    # Generate unique filename
    ext = os.path.splitext(image_file.name)[1]
    filename = f"{uuid.uuid4()}{ext}"
    file_path = f"{char_dir}/{filename}"
    
    # Save the file
    saved_path = default_storage.save(file_path, ContentFile(image_file.read()))
    
    # Create image info
    image_info = {
        'id': str(uuid.uuid4()),
        'filename': filename,
        'path': saved_path,
        'caption': caption,
        'url': default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}",
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
    """
    gallery = character.attributes.get('image_gallery', default=[], category='gallery')
    
    # Find and remove the image
    for i, img in enumerate(gallery):
        if img.get('id') == image_id:
            # Delete the file
            try:
                if default_storage.exists(img['path']):
                    default_storage.delete(img['path'])
            except Exception as e:
                logger.warning(f"Could not delete image file {img['path']}: {e}")
            
            # Remove from gallery
            gallery.pop(i)
            character.attributes.add('image_gallery', gallery, category='gallery')
            return True
    
    return False

def roster_view(request):
    """
    Main view for the character roster.
    Shows available, active, and retired characters.
    """
    # Get characters by status
    available_chars = ObjectDB.objects.filter(db_attributes__db_key='status', 
                                           db_attributes__db_value=STATUS_AVAILABLE).order_by('db_key')
    active_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                        db_attributes__db_value=STATUS_ACTIVE).order_by('db_key')
    gone_chars = ObjectDB.objects.filter(db_attributes__db_key='status',
                                      db_attributes__db_value=STATUS_GONE).order_by('db_key')
    
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

    # Helper function to get organization data for a character list
    def get_org_data(chars, org):
        org_chars = []
        for char in chars:
            try:
                # Get character's organizations safely
                char_orgs = char.attributes.get('organisations', default={}, category='organisations')
                if org.id in char_orgs:
                    rank = char_orgs[org.id]
                    rank_name = org.db.rank_names.get(rank, f"Rank {rank}")
                    org_chars.append({
                        'char': char,
                        'concept': get_concept(char),
                        'display_name': get_display_name(char),
                        'rank_name': rank_name,
                        'rank': rank  # Store rank for sorting
                    })
            except Exception:
                continue
                
        # Sort by rank (lower numbers first) then name
        return sorted(org_chars, key=lambda x: (x['rank'], x['char'].key.lower()))

    # Prepare organization data for each status
    org_data = {}
    for status, char_list in [('available', available_chars), 
                            ('active', active_chars), 
                            ('gone', gone_chars)]:
        status_orgs = []
        for org in organizations:
            org_chars = get_org_data(char_list, org)
            if org_chars:  # Only include organizations with members
                status_orgs.append((org, [
                    (char_data['char'], 
                     char_data['concept'], 
                     char_data['display_name'], 
                     char_data['rank_name']) 
                    for char_data in org_chars
                ]))
        org_data[status] = status_orgs

    # Prepare context with character data
    context = {
        'available_chars': [(char, get_concept(char), get_display_name(char)) for char in available_chars],
        'active_chars': [(char, get_concept(char), get_display_name(char)) for char in active_chars],
        'gone_chars': [(char, get_concept(char), get_display_name(char)) for char in gone_chars],
        'organizations': org_data
    }
    
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
    can_see_traits = request.user.is_staff or (request.user.username.lower() == character.name.lower())
    
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
    
    context = {
        'character': character,
        'basic_info': basic_info,
        'organizations': organizations,
        'can_see_traits': can_see_traits,
        'gallery_images': gallery_images,
    }
    
    # Only include traits if user has permission
    if can_see_traits:
        # Get character's distinctions
        distinctions = {}
        for key in character.distinctions.all():
            trait = character.distinctions.get(key)
            distinctions[trait.name or key] = {
                'key': key,
                'description': trait.desc or "No description",
                'value': f"d{int(trait.value)}"
            }
        
        # Get character's attributes
        attributes = {}
        for key in character.character_attributes.all():
            trait = character.character_attributes.get(key)
            attributes[trait.name or key] = {
                'key': key,
                'description': trait.desc or "No description",
                'value': f"d{int(trait.value)}"
            }
        
        # Get character's skills
        skills = {}
        for key in character.skills.all():
            trait = character.skills.get(key)
            skills[trait.name or key] = {
                'key': key,
                'description': trait.desc or "No description",
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
        if not request.user.is_staff:
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
            'special_effects'
        ]
        
        if field not in allowed_fields:
            return JsonResponse({'error': f'Invalid field: {field}'}, status=400)
        
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
        can_edit = request.user.is_staff or (request.user.username.lower() == character.name.lower())
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
        
        # Validate file size (max 1MB)
        if image_file.size > 1 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum size is 1MB'}, status=400)
        
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
        can_edit = request.user.is_staff or (request.user.username.lower() == character.name.lower())
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
        can_edit = request.user.is_staff or (request.user.username.lower() == character.name.lower())
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
        can_edit = request.user.is_staff or (request.user.username.lower() == character.name.lower())
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
        can_edit = request.user.is_staff or (request.user.username.lower() == character.name.lower())
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
