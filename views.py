from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.views import generic
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from registration.models import Activity
from registration.models import Lbw
from registration.models import Message
from registration.models import UserRegistration
from registration.forms import ActivityForm
from registration.forms import LbwForm
from registration.forms import LoginForm
from registration.forms import UserRegistrationForm

def login_page(request):
  message = None
  if request.method == 'POST':
    form = LoginForm(request.POST)
    if form.is_valid():
      user = authenticate(username=request.POST['username'],
                          password=request.POST['password'])
      if user:
        if user.is_active:
          login(request, user)
          if 'next' in request.POST:
            return HttpResponseRedirect(request.POST['next'])
          else:
            return HttpResponseRedirect(reverse('registration:index'))
        else:
          form.errors['username'] = 'This user is not active'
      else:
        form.errors['username'] = 'Invalid username and/or password'
  else:
    form = LoginForm()
  return render(request, 'registration/login.html', {'login_form': form})

def index(request):
  if request.method == 'POST':
    form = LbwForm(request.POST)
    if form.is_valid():
      lbw = form.save()
      lbw.owners.add(request.user)
      lbw.save()
      return HttpResponseRedirect(
          reverse('registration:detail', args=(lbw.id,)))
  else:
    form = LbwForm()
  lbws = Lbw.objects.order_by('-start_date')
  return render(
      request,
      'registration/index.html',
      {'lbws': lbws, 'form': form})

def detail(request, pk, old_form=None):
  lbw = get_object_or_404(Lbw, pk=pk)
  user_registration = None
  for ur in lbw.userregistration_set.all():
    if ur.user == request.user:
      user_registration = ur
  user_registration_form = UserRegistrationForm(instance=user_registration)
  lbw_form = LbwForm(instance=old_form)
  return render(
      request,
      'registration/detail.html',
      {'lbw': lbw, 'lbw_form': lbw_form,
       'user_registration_form': user_registration_form})

def deregister(request, lbw_id):
  current_registration = get_object_or_404(UserRegistration, lbw_id=lbw_id, user_id=request.user.id)
  current_registration.delete()
  return HttpResponseRedirect(reverse('registration:index'))

def register(request, lbw_id):
    current_registration = UserRegistration.objects.all().filter(lbw_id=lbw_id, user_id=request.user.id)
    if current_registration:
      # update instead of create
      ur = current_registration[0]
    else:
      ur = UserRegistration(user_id=request.user.id, lbw_id=lbw_id)
    user_registration_form = UserRegistrationForm(request.POST, instance=ur)
    try:
      user_registration = user_registration_form.save()
      return HttpResponseRedirect(
          reverse('registration:detail', args=(user_registration.lbw_id,)))
    except ValueError:
      return detail(request, lbw_id, user_registration_form)

def activities(request, lbw_id):
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  if request.method == 'POST':
    activity_form = ActivityForm(request.POST)
    if activity_form.is_valid():
      activity = activity_form.save()
      activity.lbw = lbw
      activity.owners.add(request.user)
      activity.save()
  else:
    activity_form = ActivityForm()
  return render(request, 'registration/activities.html',
                {'lbw': lbw, 'activity_form': activity_form})
   
def activity(request, lbw_id, activity_id):
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  activity_form = ActivityForm(instance=lbw.activity.get(pk=activity_id))
  return render(request, 'registration/activity.html',
                {'lbw': lbw, 'requested_activity_id': activity_id,
                'activity_form': activity_form})

def schedule(request, lbw_id):
    return HttpResponse("Showing schedule for lbw %s." % lbw_id)

def tshirts(request, lbw_id):
    return HttpResponse("Showing tshirts for lbw %s." % lbw_id)

def rides(request, lbw_id):
    return HttpResponse("Showing rides for lbw %s." % lbw_id)

def participants(request, lbw_id):
    return HttpResponse("Showing participants for lbw %s." % lbw_id)

def message(request, lbw_id, message_id):
    return HttpResponse("Viewing message for lbw %s, message %s." % (lbw_id, message_id))

def save_message(request, lbw_id):
    message = Message()
    message.subject = request.POST['subject']
    message.message = request.POST['message']
    message.writer = request.user
    if 'activity_id' in request.POST:
      message.activity_id = request.POST['activity_id']
    else:
      if lbw_id != request.POST['lbw_id']:
        return HttpResponseRedirect(reverse('registration:detail', args=(lbw_id,)))
      message.lbw_id = lbw_id
    message.save()
    return HttpResponseRedirect(reverse('registration:detail', args=(lbw_id,)))

def propose_activity(request, lbw_id):
    
    return HttpResponse("Proposing activity for lbw %s." % lbw_id)

def cancel_activity(request, lbw_id):
    return HttpResponse("Cancelling activity for lbw %s." % lbw_id)

def lbwuserview(request, lbw_id, user_id):
  lbw = get_object_or_404(Event, pk=lbw_id)
  return render(
      request,
      'registration/userview.html',
      {'lbw': lbw})
    
class UserView(generic.DetailView):
    model = User
    template_name = 'registration/userview.html'
