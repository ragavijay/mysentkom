from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Min, Max
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
import plotly.graph_objects as go
from plotly.offline import plot
import plotly.express as px
import pandas as pd
import requests
import json
from .models import Cluster, Post, Response, AgeGroup, AppUser, State


def is_admin(user):
    try:
        app_user = AppUser.objects.get(username=user.username)
        return app_user.usertype == 1
    except AppUser.DoesNotExist:
        return False


@require_http_methods(["GET", "POST"])
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            app_user = AppUser.objects.get(username=username)
            if app_user.passwrd == password:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': f'{username}@sentiment.local'}
                )
                login(request, user)
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'error': 'Invalid credentials'})
        except AppUser.DoesNotExist:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    posts = Post.objects.select_related('clusterid').all().order_by('-postdate')
    
    posts_data = []
    for post in posts:
        responses = Response.objects.filter(postid=post.postid)
        total = responses.count()
        
        if total > 0:
            positive = responses.filter(sentiment='P').count()
            negative = responses.filter(sentiment='N').count()
            neutral = responses.filter(sentiment='U').count()
            
            positive_pct = round((positive / total) * 100, 1)
            negative_pct = round((negative / total) * 100, 1)
            neutral_pct = round((neutral / total) * 100, 1)
        else:
            positive_pct = negative_pct = neutral_pct = 0
        
        posts_data.append({
            'post': post,
            'postdate': post.postdate,
            'total_responses': total,
            'positive_pct': positive_pct,
            'negative_pct': negative_pct,
            'neutral_pct': neutral_pct,
        })
    
    context = {
        'clusters_count': Cluster.objects.count(),
        'posts_count': Post.objects.count(),
        'responses_count': Response.objects.count(),
        'posts_data': posts_data,
        'is_admin': is_admin(request.user),
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='login')
def sentiment_analysis(request):
    post_id = request.GET.get('post', None)
    page_number = request.GET.get('page', None)
    
    gender_filter = request.GET.get('gender', '')
    agegroup_filter = request.GET.get('agegroup', '')
    state_filter = request.GET.get('state', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if not post_id:
        posts = Post.objects.select_related('clusterid').all()
        context = {
            'posts': posts,
            'selected_post': None,
            'is_admin': is_admin(request.user),
        }
        return render(request, 'sentiment_analysis.html', context)
    
    selected_post = get_object_or_404(Post, postid=post_id)
    responses = Response.objects.filter(postid=post_id).select_related('agegroupid', 'stateid', 'postid')
    
    if gender_filter:
        responses = responses.filter(gender=gender_filter)
    if agegroup_filter:
        responses = responses.filter(agegroupid__agegroupid=agegroup_filter)
    if state_filter:
        responses = responses.filter(stateid__stateid=state_filter)
    if date_from:
        responses = responses.filter(responsedate__gte=date_from)
    if date_to:
        responses = responses.filter(responsedate__lte=date_to)
    
    all_responses = Response.objects.filter(postid=post_id)
    # Get min and max dates for the date range slider
    date_range = all_responses.aggregate(
        min_date=Min('responsedate'),
        max_date=Max('responsedate')
    )
    min_date = date_range['min_date']
    max_date = date_range['max_date']
    
    # Get distinct genders from responses
    genders_list = all_responses.values_list('gender', flat=True).distinct().order_by('gender')
    # Map gender codes to labels
    gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Others', 'N': 'Not Disclosed'}
    genders = [(code, gender_map.get(code, code)) for code in genders_list]
    
    age_groups = AgeGroup.objects.filter(response__postid=post_id).distinct().order_by('agegroupid')
    # Changed: Get all states including NA (stateid >= 0)
    states = State.objects.filter(
        stateid__in=all_responses.values_list('stateid__stateid', flat=True).distinct()
    ).order_by('stateid')
    
    sentiment_data = responses.values('sentiment').annotate(count=Count('responseid'))
    sentiments = {item['sentiment']: item['count'] for item in sentiment_data}
    labels = ['Positive', 'Negative', 'Neutral']
    values = [sentiments.get('P', 0), sentiments.get('N', 0), sentiments.get('U', 0)]
    colors = ['#2ecc71', '#e74c3c', '#95a5a6']
    
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker=dict(colors=colors), hole=0.3)])
    fig.update_layout(title='Sentiment Distribution', height=500)
    sentiment_chart = plot(fig, output_type='div', include_plotlyjs=False)
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        if page_number:
            responses_list = responses.order_by('-responsedate')
            paginator = Paginator(responses_list, 5)
            
            try:
                page_number = int(page_number)
            except (TypeError, ValueError):
                page_number = 1
            
            try:
                responses_page = paginator.page(page_number)
            except:
                responses_page = paginator.page(1)
            
            html = render_to_string('responses_list.html', {
                'responses_page': responses_page,
                'selected_post_id': post_id,
                'total_responses': responses.count(),
            })
            return JsonResponse({'html': html})
        else:
            return JsonResponse({
                'sentiment_chart': sentiment_chart,
                'total_responses': responses.count()
            })
    
    responses_list = responses.order_by('-responsedate')
    paginator = Paginator(responses_list, 5)
    
    try:
        page_num = int(page_number) if page_number else 1
    except (TypeError, ValueError):
        page_num = 1
    
    try:
        responses_page = paginator.page(page_num)
    except:
        responses_page = paginator.page(1)
    
    posts = Post.objects.select_related('clusterid').all()
    
    context = {
        'sentiment_chart': sentiment_chart,
        'posts': posts,
        'selected_post': selected_post,
        'selected_post_id': post_id,
        'total_responses': responses.count(),
        'responses_page': responses_page,
        'genders': genders,
        'age_groups': age_groups,
        'states': states,
        'gender_filter': gender_filter,
        'agegroup_filter': agegroup_filter,
        'state_filter': state_filter,
        'date_from': date_from,
        'date_to': date_to,
        'min_date': min_date,
        'max_date': max_date,
        'is_admin': is_admin(request.user),
    }
    return render(request, 'sentiment_analysis.html', context)


@login_required(login_url='login')
def cluster_analysis(request):
    clusters = Cluster.objects.annotate(post_count=Count('post'))
    cluster_names = [c.clustername for c in clusters]
    post_counts = [c.post_count for c in clusters]
    
    fig = go.Figure(data=[go.Bar(x=cluster_names, y=post_counts, marker=dict(color='#3498db'))])
    fig.update_layout(title='Posts per Cluster', xaxis_title='Cluster', yaxis_title='Number of Posts', height=400)
    cluster_chart = plot(fig, output_type='div', include_plotlyjs=False)
    
    context = {
        'cluster_chart': cluster_chart,
        'is_admin': is_admin(request.user),
    }
    return render(request, 'cluster_analysis.html', context)


@login_required(login_url='login')
def demographic_analysis(request):
    post_id = request.GET.get('post', None)
    posts = Post.objects.select_related('clusterid').all()

    if not post_id:
        context = {
            'posts': posts,
            'selected_post': None,
            'is_admin': is_admin(request.user),
        }
        return render(request, 'demographic_analysis.html', context)

    selected_post = get_object_or_404(Post, postid=post_id)
    responses = Response.objects.filter(postid=post_id)

    # ---------- State-wise sentiment distribution ----------
    state_data = []
    states = State.objects.filter(stateid__gt=0).order_by('statename')

    for state in states:
        state_responses = responses.filter(stateid=state)
        total = state_responses.count()

        if total > 0:
            positive = state_responses.filter(sentiment='P').count()
            negative = state_responses.filter(sentiment='N').count()
            neutral = state_responses.filter(sentiment='U').count()

            state_data.append({
                'state': state.statename,
                'total': total,
                'positive': positive,
                'negative': negative,
                'neutral': neutral,
                'positive_pct': round((positive / total) * 100, 1),
                'negative_pct': round((negative / total) * 100, 1),
                'neutral_pct': round((neutral / total) * 100, 1),
            })

    # ---------- Gender distribution ----------
    gender_sentiment = responses.values('gender', 'sentiment').annotate(count=Count('responseid'))
    genders = ['M', 'F', 'O', 'N']
    gender_labels = ['Male', 'Female', 'Others', 'Not Disclosed']
    positive = [0, 0, 0, 0]
    negative = [0, 0, 0, 0]
    neutral = [0, 0, 0, 0]

    for item in gender_sentiment:
        idx = genders.index(item['gender']) if item['gender'] in genders else -1
        if idx >= 0:
            if item['sentiment'] == 'P':
                positive[idx] = item['count']
            elif item['sentiment'] == 'N':
                negative[idx] = item['count']
            elif item['sentiment'] == 'U':
                neutral[idx] = item['count']

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Positive', x=gender_labels, y=positive, marker=dict(color='#2ecc71')))
    fig.add_trace(go.Bar(name='Negative', x=gender_labels, y=negative, marker=dict(color='#e74c3c')))
    fig.add_trace(go.Bar(name='Neutral', x=gender_labels, y=neutral, marker=dict(color='#95a5a6')))
    fig.update_layout(title='Sentiment by Gender', barmode='group', height=400)
    gender_chart = plot(fig, output_type='div', include_plotlyjs=False)

    # ---------- Age group distribution ----------
    age_sentiment = responses.exclude(agegroupid__agegroupid=0).values(
        'agegroupid__agegroup', 'sentiment'
    ).annotate(count=Count('responseid'))

    age_groups_list = AgeGroup.objects.filter(agegroupid__gt=0).order_by('agegroupid')
    age_labels = [ag.agegroup for ag in age_groups_list]
    age_positive = [0] * len(age_labels)
    age_negative = [0] * len(age_labels)
    age_neutral = [0] * len(age_labels)

    for item in age_sentiment:
        try:
            idx = age_labels.index(item['agegroupid__agegroup'])
            if item['sentiment'] == 'P':
                age_positive[idx] = item['count']
            elif item['sentiment'] == 'N':
                age_negative[idx] = item['count']
            elif item['sentiment'] == 'U':
                age_neutral[idx] = item['count']
        except ValueError:
            pass

    age_fig = go.Figure()
    age_fig.add_trace(go.Bar(name='Positive', x=age_labels, y=age_positive, marker=dict(color='#2ecc71')))
    age_fig.add_trace(go.Bar(name='Negative', x=age_labels, y=age_negative, marker=dict(color='#e74c3c')))
    age_fig.add_trace(go.Bar(name='Neutral', x=age_labels, y=age_neutral, marker=dict(color='#95a5a6')))
    age_fig.update_layout(title='Sentiment by Age Group', barmode='group', height=400)
    age_chart = plot(age_fig, output_type='div', include_plotlyjs=False)

    # ---------- Malaysia State Map ----------
    if state_data:
        # Normalize names to match GeoJSON
        name_map = {
            "Penang": "Pulau Pinang",
            "WP Kuala Lumpur": "Kuala Lumpur",
            "WP Labuan": "Labuan",
            "WP Putrajaya": "Putrajaya",
        }
        for s in state_data:
            if s['state'] in name_map:
                s['state'] = name_map[s['state']]

        # Load GeoJSON for Malaysian states
        geojson_url = "https://raw.githubusercontent.com/ragavijay/mysentkom/main/static/geojson/malaysia_states.geojson.geojson"
        response = requests.get(geojson_url)
        print(response.status_code)
        print(response.text[:500])
        malaysia_geojson = response.json()

        # Convert to DataFrame for Plotly Express
        df = pd.DataFrame(state_data)

        fig_map = px.choropleth_mapbox(
            df,
            geojson=malaysia_geojson,
            locations='state',
            color='total',
            featureidkey="properties.name",
            hover_name='state',
            hover_data={
                'total': True,
                'positive': True,
                'negative': True,
                'neutral': True,
                'positive_pct': True,
                'negative_pct': True,
                'neutral_pct': True,
            },
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            center={"lat": 4.2105, "lon": 101.9758},
            zoom=4.3,
            title="Response Distribution by Malaysian States"
        )

        map_chart = plot(fig_map, output_type='div', include_plotlyjs=False)
    else:
        map_chart = None

    # ---------- Final context ----------
    context = {
        'posts': posts,
        'selected_post': selected_post,
        'selected_post_id': post_id,
        'state_data': state_data,
        'map_chart': map_chart,
        'gender_chart': gender_chart,
        'age_chart': age_chart,
        'is_admin': is_admin(request.user),
    }

    return render(request, 'demographic_analysis.html', context)


@login_required(login_url='login')
def manage_clusters(request):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    clusters = Cluster.objects.annotate(post_count=Count('post')).order_by('-clusterid')
    context = {
        'clusters': clusters,
        'is_admin': True,
    }
    return render(request, 'manage_clusters.html', context)


@login_required(login_url='login')
def add_cluster(request):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        clustername = request.POST.get('clustername')
        if clustername:
            Cluster.objects.create(clustername=clustername)
            messages.success(request, 'Cluster added successfully!')
            return redirect('manage_clusters')
    
    context = {'is_admin': True}
    return render(request, 'add_cluster.html', context)


@login_required(login_url='login')
def edit_cluster(request, cluster_id):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    cluster = get_object_or_404(Cluster, clusterid=cluster_id)
    
    if request.method == 'POST':
        clustername = request.POST.get('clustername')
        if clustername:
            cluster.clustername = clustername
            cluster.save()
            messages.success(request, 'Cluster updated successfully!')
            return redirect('manage_clusters')
    
    context = {
        'cluster': cluster,
        'is_admin': True,
    }
    return render(request, 'edit_cluster.html', context)


@login_required(login_url='login')
def delete_cluster(request, cluster_id):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    cluster = get_object_or_404(Cluster, clusterid=cluster_id)
    if request.method == 'POST':
        cluster.delete()
        messages.success(request, 'Cluster deleted successfully!')
        return redirect('manage_clusters')
    
    context = {
        'cluster': cluster,
        'is_admin': True,
    }
    return render(request, 'delete_cluster.html', context)


@login_required(login_url='login')
def manage_posts(request):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    cluster_id = request.GET.get('cluster', None)
    if cluster_id:
        posts = Post.objects.filter(clusterid=cluster_id).select_related('clusterid').order_by('-postid')
    else:
        posts = Post.objects.select_related('clusterid').order_by('-postid')
    
    clusters = Cluster.objects.all()
    context = {
        'posts': posts,
        'clusters': clusters,
        'selected_cluster': cluster_id,
        'is_admin': True,
    }
    return render(request, 'manage_posts.html', context)


@login_required(login_url='login')
def add_post(request):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        cluster_id = request.POST.get('clusterid')
        postlink = request.POST.get('postlink')
        postmessage = request.POST.get('postmessage')
        postdate = request.POST.get('postdate')  # New: Added postdate field
        
        if cluster_id and postlink and postmessage and postdate:
            cluster = get_object_or_404(Cluster, clusterid=cluster_id)
            Post.objects.create(clusterid=cluster, postlink=postlink, postmessage=postmessage, postdate=postdate)
            messages.success(request, 'Post added successfully!')
            return redirect('manage_posts')
        else:
            messages.error(request, 'All fields are required!')
    
    clusters = Cluster.objects.all()
    context = {
        'clusters': clusters,
        'is_admin': True,
    }
    return render(request, 'add_post.html', context)


@login_required(login_url='login')
def edit_post(request, post_id):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    post = get_object_or_404(Post, postid=post_id)
    
    if request.method == 'POST':
        cluster_id = request.POST.get('clusterid')
        postlink = request.POST.get('postlink')
        postmessage = request.POST.get('postmessage')
        postdate = request.POST.get('postdate')  # New: Added postdate field
        
        if cluster_id and postlink and postmessage and postdate:
            cluster = get_object_or_404(Cluster, clusterid=cluster_id)
            post.clusterid = cluster
            post.postlink = postlink
            post.postmessage = postmessage
            post.postdate = postdate
            post.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('manage_posts')
        else:
            messages.error(request, 'All fields are required!')
    
    clusters = Cluster.objects.all()
    context = {
        'post': post,
        'clusters': clusters,
        'is_admin': True,
    }
    return render(request, 'edit_post.html', context)


@login_required(login_url='login')
def delete_post(request, post_id):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    post = get_object_or_404(Post, postid=post_id)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('manage_posts')
    
    context = {
        'post': post,
        'is_admin': True,
    }
    return render(request, 'delete_post.html', context)