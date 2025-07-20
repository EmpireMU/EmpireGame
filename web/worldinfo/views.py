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
    
    return user.is_staff or user.check_permstring("Admin") or user.check_permstring("Builder")


def worldinfo_index(request):
    """Main worldinfo page showing all public pages and categories."""
    is_staff = is_staff_user(request.user)
    
    # Get pages (public for everyone, all for staff)
    if is_staff:
        pages = WorldInfoPage.objects.all()
    else:
        pages = WorldInfoPage.objects.filter(is_public=True)
    
    # Define custom category ordering
    CATEGORY_ORDER = [
        'Introduction',
        'World Overview',
        'Houses of the Empire',
        'Other Organisations',
        'The City of Sanctuary',
        'Lands Beyond the Empire'
    ]
    
    def get_category_order(category):
        """Return the sort order for a category. Unknown categories get sorted to the end."""
        try:
            return CATEGORY_ORDER.index(category)
        except ValueError:
            return len(CATEGORY_ORDER)  # Unknown categories go to the end
    
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
    
    # Sort categories by custom order, then subcategories alphabetically
    sorted_categories = {}
    for category in sorted(categories.keys(), key=get_category_order):
        sorted_subcategories = {}
        for subcategory in sorted(categories[category].keys()):
            sorted_subcategories[subcategory] = categories[category][subcategory]
        sorted_categories[category] = sorted_subcategories
    
    context = {
        'categories': sorted_categories,
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


def worldinfo_search_view(request):
    """
    Search worldinfo pages by title and content.
    Standalone search functionality that doesn't interfere with existing worldinfo.
    """
    query = request.GET.get('q', '').strip()
    results = []
    
    if query and len(query) >= 2:  # Minimum 2 characters to search
        # Check if user is staff (same pattern as other worldinfo views)
        is_staff = is_staff_user(request.user)
        
        # Get pages based on permissions (same pattern as worldinfo_index)
        if is_staff:
            pages = WorldInfoPage.objects.all()
        else:
            pages = WorldInfoPage.objects.filter(is_public=True)
        
        # Search through pages
        query_lower = query.lower()
        
        for page in pages:
            match_score = 0
            matched_fields = []
            
            # Search page title (highest priority)
            if query_lower in page.title.lower():
                match_score += 10
                matched_fields.append('title')
            
            # Search page content
            if query_lower in page.content.lower():
                match_score += 5
                matched_fields.append('content')
            
            # Search category and subcategory
            if page.category and query_lower in page.category.lower():
                match_score += 3
                matched_fields.append('category')
            
            if page.subcategory and query_lower in page.subcategory.lower():
                match_score += 3
                matched_fields.append('subcategory')
            
            # If we found any matches, add to results
            if match_score > 0:
                # Create a snippet from content showing relevant context
                snippet = ""
                if 'content' in matched_fields:
                    # Find the first occurrence of the query in content
                    content_lower = page.content.lower()
                    query_pos = content_lower.find(query_lower)
                    if query_pos >= 0:
                        # Get context around the match (50 characters before and after)
                        start = max(0, query_pos - 50)
                        end = min(len(page.content), query_pos + len(query) + 50)
                        snippet = page.content[start:end].strip()
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(page.content):
                            snippet = snippet + "..."
                
                # If no content snippet, use beginning of content
                if not snippet and page.content:
                    snippet = page.content[:150] + "..." if len(page.content) > 150 else page.content
                
                results.append({
                    'page': page,
                    'title': page.title,
                    'category': page.category or 'General',
                    'subcategory': page.subcategory or 'General',
                    'score': match_score,
                    'matched_fields': matched_fields,
                    'snippet': snippet,
                    'is_public': page.is_public
                })
        
        # Sort results by score (highest first), then by title
        results.sort(key=lambda x: (-x['score'], x['title'].lower()))
    
    context = {
        'query': query,
        'results': results,
        'result_count': len(results),
        'is_staff': is_staff_user(request.user),
    }
    
    return render(request, 'worldinfo/search.html', context) 