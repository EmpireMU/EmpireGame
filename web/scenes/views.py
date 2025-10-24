"""Web views for browsing scene logs."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from web.scenes.models import SceneEntry, SceneLog
from utils import scene_logger


class SceneListView(View):
    """Display the scenes available to the current user/thread."""

    template_name = "website/scenes/scene_list.html"
    paginate_by = 25

    def get(self, request):
        queryset = SceneLog.objects.filter(status__in=[SceneLog.Status.ACTIVE, SceneLog.Status.COMPLETED])
        visibility_filter = Q(visibility=SceneLog.Visibility.EVENT)
        if request.user.is_authenticated:
            visibility_filter |= Q(participants__account=request.user)
            visibility_filter |= Q(visibility=SceneLog.Visibility.ORGANISATION, organisations__in=self._user_org_ids(request))
        queryset = queryset.filter(visibility_filter).distinct()
        queryset = self._apply_filters(request, queryset)
        paginator = Paginator(queryset, self.paginate_by)
        page = paginator.get_page(request.GET.get("page"))
        context = {
            "page_obj": page,
            "paginator": paginator,
            "object_list": page.object_list,
            "filters": {
                "chapter": request.GET.get("chapter", ""),
                "plot": request.GET.get("plot", ""),
                "keyword": request.GET.get("q", ""),
                "visibility": request.GET.get("visibility", ""),
            },
        }
        return render(request, self.template_name, context)

    def _apply_filters(self, request, queryset):
        chapter = request.GET.get("chapter")
        plot = request.GET.get("plot")
        keyword = request.GET.get("q")
        visibility = request.GET.get("visibility")
        if chapter:
            queryset = queryset.filter(chapter__db__story_id__iexact=chapter)
        if plot:
            queryset = queryset.filter(plots__db__story_id__iexact=plot)
        if keyword:
            queryset = queryset.filter(Q(title__icontains=keyword) | Q(entries__text_plain__icontains=keyword))
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        return queryset

    def _user_org_ids(self, request):
        if not request.user.is_authenticated:
            return []
        from utils.org_utils import get_account_organisations

        return list(get_account_organisations(request.user))


class SceneDetailView(View):
    """Detail view showing metadata and filtered transcript."""

    template_name = "website/scenes/scene_detail.html"

    def get(self, request, pk):
        scene = get_object_or_404(SceneLog, pk=pk)
        if not scene_logger.scene_allows_viewer(scene, request.user):
            if not request.user.is_authenticated:
                raise Http404
            raise Http404
        entries = scene_logger.visible_entries_for_account(scene, request.user)
        context = {
            "scene": scene,
            "entries": entries,
        }
        return render(request, self.template_name, context)


class SceneDownloadView(View):
    """Provide a text download of the visible transcript."""

    def get(self, request, pk):
        scene = get_object_or_404(SceneLog, pk=pk)
        if not scene_logger.scene_allows_viewer(scene, request.user):
            raise Http404
        entries = scene_logger.visible_entries_for_account(scene, request.user)
        lines = [entry.text_plain for entry in entries.order_by("sequence")]
        content = "\n".join(lines)
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = f"attachment; filename=scene-{scene.pk}.txt"
        return response
