from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from evennia.objects.models import ObjectDB
from .models import FamilyRelationship, RECIPROCAL_RELATIONSHIPS


def is_staff_user(user):
    """Check if user is Django staff or Evennia Builder+"""
    if user.is_staff:
        return True
    if hasattr(user, 'account') and user.account:
        return user.account.check_permstring("Builder")
    return False


@login_required
def character_search(request):
    """
    AJAX endpoint for character autocomplete.
    Returns JSON list of characters matching the search query.
    """
    # Check if user is staff
    if not is_staff_user(request.user):
        return HttpResponseForbidden("Access denied")
    
    query = request.GET.get('q', '').strip()
    
    # Require at least 2 characters to search
    if len(query) < 2:
        return JsonResponse([])
    
    # Limit query length for security
    query = query[:50]
    
    # Search for characters (case-insensitive)
    characters = ObjectDB.objects.filter(
        db_attributes__db_key='status',
        db_key__icontains=query
    ).exclude(
        db_attributes__db_value='gone'
    ).values('id', 'db_key').order_by('db_key')[:10]
    
    # Filter out staff accounts
    results = []
    for char_data in characters:
        try:
            char = ObjectDB.objects.get(id=char_data['id'])
            if not (char.account and char.account.check_permstring("Builder")):
                # Get display name (full_name if available, otherwise db_key)
                display_name = char.db.full_name or char.db_key
                results.append({
                    'id': char_data['id'],
                    'name': char_data['db_key'],
                    'display_name': display_name
                })
        except ObjectDB.DoesNotExist:
            continue
    
    return JsonResponse(results, safe=False)


@login_required
def get_character_name(request):
    """
    Get character name by ID for displaying existing relationships.
    """
    # Check if user is staff
    if not is_staff_user(request.user):
        return HttpResponseForbidden("Access denied")
    
    char_id = request.GET.get('id')
    if not char_id:
        return JsonResponse({'error': 'No character ID provided'}, status=400)
    
    try:
        char = ObjectDB.objects.get(id=char_id)
        display_name = char.db.full_name or char.db_key
        return JsonResponse({
            'id': char.id,
            'name': char.db_key,
            'display_name': display_name
        })
    except ObjectDB.DoesNotExist:
        return JsonResponse({'error': 'Character not found'}, status=404)


@login_required
def relationship_list(request):
    """
    Main view showing all family relationships, with forms to add new ones.
    Staff only.
    """
    # Check if user is staff
    if not is_staff_user(request.user):
        return HttpResponseForbidden("You must be staff to access family relationship management.")
    relationships = FamilyRelationship.objects.all()
    
    # No longer need to load all characters - autocomplete handles this
    context = {
        'relationships': relationships,
        'relationship_choices': FamilyRelationship._meta.get_field('relationship_type').choices,
    }
    
    return render(request, 'relationships/relationship_list.html', context)


@login_required
@require_POST
@csrf_protect
def add_relationship(request):
    """
    Add a new family relationship.
    Staff only.
    """
    # Check if user is staff
    if not is_staff_user(request.user):
        return HttpResponseForbidden("You must be staff to manage family relationships.")
    character_id = request.POST.get('character_id')
    relationship_type = request.POST.get('relationship_type')
    related_type = request.POST.get('related_type')  # 'pc' or 'npc'
    related_name = request.POST.get('related_name', '').strip()
    create_reciprocal = request.POST.get('create_reciprocal') == 'on'
    
    # Validate inputs
    if not all([character_id, relationship_type, related_name]):
        messages.error(request, "All fields are required.")
        return redirect('relationships:list')
    
    # Validate character exists
    try:
        character = ObjectDB.objects.get(id=character_id)
    except ObjectDB.DoesNotExist:
        messages.error(request, "Selected character not found.")
        return redirect('relationships:list')
    
    # Process based on related character type
    related_character_id = None
    related_character_name = related_name
    
    if related_type == 'pc':
        # Find PC by name
        try:
            related_char = ObjectDB.objects.get(db_key__iexact=related_name)
            related_character_id = related_char.id
            related_character_name = ''  # Clear name since we have ID
        except ObjectDB.DoesNotExist:
            messages.error(request, f"No player character found with name '{related_name}'.")
            return redirect('relationships:list')
        except ObjectDB.MultipleObjectsReturned:
            messages.error(request, f"Multiple characters found with name '{related_name}'. Please be more specific.")
            return redirect('relationships:list')
    
    # Create the main relationship
    try:
        relationship = FamilyRelationship.objects.create(
            character_id=character_id,
            related_character_id=related_character_id,
            related_character_name=related_character_name,
            relationship_type=relationship_type
        )
        
        char_name = character.db.full_name or character.name
        related_display = related_name if related_type == 'npc' else f"{related_name} (PC)"
        messages.success(request, f"Added {relationship.get_relationship_type_display().lower()} relationship: {char_name} → {related_display}")
        
        # Create reciprocal relationship if requested and it's a PC
        if create_reciprocal and related_character_id and relationship_type in RECIPROCAL_RELATIONSHIPS:
            reciprocal_type = RECIPROCAL_RELATIONSHIPS[relationship_type]
            
            # Check if reciprocal already exists
            existing_reciprocal = FamilyRelationship.objects.filter(
                character_id=related_character_id,
                related_character_id=character_id,
                relationship_type=reciprocal_type
            ).first()
            
            if not existing_reciprocal:
                FamilyRelationship.objects.create(
                    character_id=related_character_id,
                    related_character_id=character_id,
                    related_character_name='',
                    relationship_type=reciprocal_type
                )
                messages.success(request, f"Also created reciprocal relationship: {related_name} → {char_name}")
        
    except Exception as e:
        messages.error(request, f"Error creating relationship: {str(e)}")
    
    return redirect('relationships:list')


@login_required
@require_POST
@csrf_protect
def delete_relationship(request, relationship_id):
    """
    Delete a family relationship.
    Staff only.
    """
    # Check if user is staff
    if not is_staff_user(request.user):
        return HttpResponseForbidden("You must be staff to manage family relationships.")
    relationship = get_object_or_404(FamilyRelationship, id=relationship_id)
    delete_reciprocal = request.POST.get('delete_reciprocal') == 'on'
    
    # Get character names for messages
    try:
        char = ObjectDB.objects.get(id=relationship.character_id)
        char_name = char.db.full_name or char.name
    except ObjectDB.DoesNotExist:
        char_name = f"Unknown (ID: {relationship.character_id})"
    
    related_name = relationship.get_related_character_display_name()
    relationship_display = relationship.get_relationship_type_display()
    
    # Delete reciprocal if requested and it's a PC relationship
    reciprocal_deleted = False
    if delete_reciprocal and relationship.related_character_id:
        reciprocal_type = RECIPROCAL_RELATIONSHIPS.get(relationship.relationship_type)
        if reciprocal_type:
            reciprocal = FamilyRelationship.objects.filter(
                character_id=relationship.related_character_id,
                related_character_id=relationship.character_id,
                relationship_type=reciprocal_type
            ).first()
            if reciprocal:
                reciprocal.delete()
                reciprocal_deleted = True
    
    # Delete the main relationship
    relationship.delete()
    
    messages.success(request, f"Deleted relationship: {char_name}'s {relationship_display.lower()} {related_name}")
    if reciprocal_deleted:
        messages.success(request, f"Also deleted reciprocal relationship")
    
    return redirect('relationships:list')


def get_character_family(character_id):
    """
    Utility function to get all family relationships for a character.
    Returns a dictionary organized by relationship type.
    """
    relationships = FamilyRelationship.objects.filter(character_id=character_id)
    
    family_dict = {}
    for relationship in relationships:
        rel_type = relationship.get_relationship_type_display()
        if rel_type not in family_dict:
            family_dict[rel_type] = []
        
        family_member = {
            'name': relationship.get_related_character_display_name(),
            'is_pc': relationship.is_related_to_pc(),
            'character_object': relationship.get_related_character_object()
        }
        family_dict[rel_type].append(family_member)
    
    return family_dict 