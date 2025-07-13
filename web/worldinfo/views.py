from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import WorldInfoPage
import re
import markdown


def is_staff_user(user):
    """Check if user has staff permissions (either Django staff or Evennia Builder+)"""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    # Check if user has an Evennia account with Builder+ permissions
    try:
        if hasattr(user, 'evennia_account') and user.evennia_account:
            return user.evennia_account.check_permstring("Builder")
    except:
        pass
    return False


def worldinfo_index(request):
    """Main worldinfo page showing all public pages and categories."""
    is_staff = is_staff_user(request.user)
    
    # Get pages (public for everyone, all for staff)
    if is_staff:
        pages = WorldInfoPage.objects.all()
    else:
        pages = WorldInfoPage.objects.filter(is_public=True)
    
    # Group pages by category and subcategory
    categories = {}
    for page in pages:
        category = page.category or 'General'
        subcategory = page.subcategory or 'General'
        
        if category not in categories:
            categories[category] = {}
        
        if subcategory not in categories[category]:
            categories[category][subcategory] = []
        
        categories[category][subcategory].append(page)
    
    context = {
        'categories': categories,
        'is_staff': is_staff,
        'page_count': pages.count(),
    }
    return render(request, 'worldinfo/index.html', context)


def worldinfo_page(request, slug):
    """Display a specific worldinfo page."""
    page = get_object_or_404(WorldInfoPage, slug=slug)
    
    # Check permissions
    if not page.is_public and not is_staff_user(request.user):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('worldinfo:index')
    
    # Process character links in content
    content = process_character_links(page.content)
    
    context = {
        'page': page,
        'content': content,
        'is_staff': is_staff_user(request.user),
    }
    return render(request, 'worldinfo/page.html', context)


@login_required
def create_page(request):
    """Create a new worldinfo page."""
    if not is_staff_user(request.user):
        messages.error(request, "You don't have permission to create pages.")
        return redirect('worldinfo:index')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', '').strip()
        subcategory = request.POST.get('subcategory', '').strip()
        is_public = request.POST.get('is_public') == 'on'
        
        if not title:
            messages.error(request, "Title is required.")
        elif not content:
            messages.error(request, "Content is required.")
        else:
            try:
                page = WorldInfoPage.objects.create(
                    title=title,
                    content=content,
                    category=category,
                    subcategory=subcategory,
                    is_public=is_public
                )
                messages.success(request, f"Page '{title}' created successfully!")
                return redirect('worldinfo:page', slug=page.slug)
            except Exception as e:
                messages.error(request, f"Error creating page: {e}")
    
    context = {
        'is_staff': True,
    }
    return render(request, 'worldinfo/create.html', context)


@login_required
def edit_page(request, slug):
    """Edit an existing worldinfo page."""
    if not is_staff_user(request.user):
        messages.error(request, "You don't have permission to edit pages.")
        return redirect('worldinfo:index')
    
    page = get_object_or_404(WorldInfoPage, slug=slug)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', '').strip()
        subcategory = request.POST.get('subcategory', '').strip()
        is_public = request.POST.get('is_public') == 'on'
        
        if not title:
            messages.error(request, "Title is required.")
        elif not content:
            messages.error(request, "Content is required.")
        else:
            try:
                page.title = title
                page.content = content
                page.category = category
                page.subcategory = subcategory
                page.is_public = is_public
                page.save()
                messages.success(request, f"Page '{title}' updated successfully!")
                return redirect('worldinfo:page', slug=page.slug)
            except Exception as e:
                messages.error(request, f"Error updating page: {e}")
    
    context = {
        'page': page,
        'is_staff': True,
    }
    return render(request, 'worldinfo/edit.html', context)


@login_required
def delete_page(request, slug):
    """Delete a worldinfo page."""
    if not is_staff_user(request.user):
        messages.error(request, "You don't have permission to delete pages.")
        return redirect('worldinfo:index')
    
    page = get_object_or_404(WorldInfoPage, slug=slug)
    
    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            title = page.title
            page.delete()
            messages.success(request, f"Page '{title}' has been deleted.")
            return redirect('worldinfo:index')
        else:
            messages.info(request, "Page deletion cancelled.")
            return redirect('worldinfo:page', slug=slug)
    
    context = {
        'page': page,
        'is_staff': True,
    }
    return render(request, 'worldinfo/delete.html', context)


def process_character_links(content):
    """Convert markdown formatting and [[Character Name]] syntax to HTML."""
    # First process markdown formatting (bold, italic, etc.)
    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    html_content = md.convert(content)
    
    # Then process character links
    def replace_character_link(match):
        char_name = match.group(1)
        # Create a link to the character roster search
        # You can modify this to link directly to specific characters if you have that data
        return f'<a href="/characters/" title="Find {char_name} in character roster">{char_name}</a>'
    
    # Replace [[Character Name]] with links
    return re.sub(r'\[\[([^\]]+)\]\]', replace_character_link, html_content) 