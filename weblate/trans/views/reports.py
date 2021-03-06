# -*- coding: utf-8 -*-
#
# Copyright © 2012 - 2015 Michal Čihař <michal@cihar.com>
#
# This file is part of Weblate <https://weblate.org/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from weblate.trans.models.changes import Change
from weblate.trans.forms import ReportsForm
from weblate.trans.views.helper import get_subproject
from weblate.trans.permissions import can_view_reports
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def generate_credits(component, start_date, end_date):
    """Generates credits data for given component."""

    result = []

    for translation in component.translation_set.all():
        authors = Change.objects.content().filter(
            translation=translation,
            timestamp__range=(start_date, end_date),
        ).values_list(
            'author__email', 'author__first_name'
        )
        if not authors:
            continue
        result.append({translation.language.name: sorted(set(authors))})

    return result


@login_required
@require_POST
def get_credits(request, project, subproject):
    """View for credits"""
    obj = get_subproject(request, project, subproject)

    if not can_view_reports(request.user, obj.project):
        raise PermissionDenied()

    form = ReportsForm(request.POST)

    if not form.is_valid():
        return redirect(obj)

    data = generate_credits(
        obj,
        form.cleaned_data['start_date'],
        form.cleaned_data['end_date'],
    )

    if form.cleaned_data['style'] == 'json':
        return JsonResponse(data=data, safe=False)

    if form.cleaned_data['style'] == 'html':
        start = '<table>'
        row_start = '<tr>'
        language_format = u'<th>{0}</th>'
        translator_start = '<td><ul>'
        translator_format = u'<li><a href="mailto:{0}">{1}</a></li>'
        translator_end = '</ul></td>'
        row_end = '</tr>'
        mime = 'text/html'
        end = '</table>'
    else:
        start = ''
        row_start = ''
        language_format = u'* {0}\n'
        translator_start = ''
        translator_format = u'    * {1} <{0}>'
        translator_end = ''
        row_end = ''
        mime = 'text/plain'
        end = ''

    result = []

    result.append(start)

    for language in data:
        name, translators = language.items()[0]
        result.append(row_start)
        result.append(language_format.format(name))
        result.append(
            u'{0}{1}{2}'.format(
                translator_start,
                '\n'.join(
                    [translator_format.format(*t) for t in translators]
                ),
                translator_end,
            )
        )
        result.append(row_end)

    result.append(end)

    return HttpResponse(
        '\n'.join(result),
        content_type='{0}; charset=utf-8'.format(mime),
    )


def generate_counts(component, start_date, end_date):
    """Generates credits data for given component."""

    result = {}

    for translation in component.translation_set.all():
        authors = Change.objects.content().filter(
            translation=translation,
            timestamp__range=(start_date, end_date),
        ).values_list(
            'author__email', 'author__first_name', 'unit__num_words',
        )
        for email, name, words in authors:
            if words is None:
                continue
            if email not in result:
                result[email] = {
                    'name': name,
                    'email': email,
                    'words': words,
                    'count': 1,
                }
            else:
                result[email]['words'] += words
                result[email]['count'] += 1

    return result.values()


@login_required
@require_POST
def get_counts(request, project, subproject):
    """View for work counts"""
    obj = get_subproject(request, project, subproject)

    if not can_view_reports(request.user, obj.project):
        raise PermissionDenied()

    form = ReportsForm(request.POST)

    if not form.is_valid():
        return redirect(obj)

    data = generate_counts(
        obj,
        form.cleaned_data['start_date'],
        form.cleaned_data['end_date'],
    )

    if form.cleaned_data['style'] == 'json':
        return JsonResponse(data=data, safe=False)

    if form.cleaned_data['style'] == 'html':
        start = (
            '<table>\n<tr><th>Email</th><th>Name</th>'
            '<th>Words</th><th>Count</th></tr>'
        )
        row_start = '<tr>'
        cell_format = u'<td>{0}</td>\n'
        row_end = '</tr>'
        mime = 'text/html'
        end = '</table>'
    else:
        heading = ' '.join(['=' * 25] * 4)
        start = '{0}\n{1:25} {2:25} {3:25} {4:25}\n{0}'.format(
            heading,
            'Email',
            'Name',
            'Words',
            'Count'
        )
        row_start = ''
        cell_format = u'{0:25} '
        row_end = ''
        mime = 'text/plain'
        end = heading

    result = []

    result.append(start)

    for item in data:
        result.append(row_start)
        result.append(
            u'{0}{1}{2}{3}'.format(
                cell_format.format(item['name']),
                cell_format.format(item['email']),
                cell_format.format(item['words']),
                cell_format.format(item['count']),
            )
        )
        result.append(row_end)

    result.append(end)

    return HttpResponse(
        '\n'.join(result),
        content_type='{0}; charset=utf-8'.format(mime),
    )
