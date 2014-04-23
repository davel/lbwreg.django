"""Views for LBW."""
import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import StreamingHttpResponse, HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.timezone import UTC

from registration.models import Accommodation
from registration.models import Activity
from registration.models import Lbw
from registration.models import Message
from registration.models import UserRegistration
from registration.forms import ActivityForm
from registration.forms import AccommodationForm
from registration.forms import DeleteLbwForm
from registration.forms import LbwForm
from registration.forms import MessageForm
from registration.forms import UserRegistrationForm

def index(request):
  """Print out an index of the known LBWs."""
  if request.user.is_authenticated():
    no_owning = Lbw.objects.exclude(owners__in=[request.user.lbwuser])
    no_attending = no_owning.exclude(attendees__in=[request.user])
    lbws = no_attending.order_by('-start_date')
  else:
    lbws = Lbw.objects.order_by('-start_date')
  return render(
      request,
      'registration/index.html',
      {'lbws': lbws})

def detail(request, lbw_id):
  """Print out a particular LBW."""
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  user_registration_form = None
  lbw_messages = None
  if request.user.is_authenticated():
    lbw_messages = Message.objects.filter(lbw=lbw).filter(activity=None)
  return render(
      request,
      'registration/detail.html',
      {'lbw': lbw,
       'lbws': lbws,
       'lbw_messages': lbw_messages})

def deregister(request, lbw_id):
  """Deregister a user from an LBW."""
  current_registration = get_object_or_404(
      UserRegistration, lbw_id=lbw_id, user=request.user)
  current_registration.delete()
  return HttpResponseRedirect(reverse('registration:detail',
                              args=(lbw_id,)))

def register(request, lbw_id):
  """Register or update a registration for an LBW."""
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  if request.method == 'POST':
    current_registration = UserRegistration.objects.all().filter(
        lbw_id=lbw_id, user=request.user)
    if current_registration:
      # update instead of create
      registration = current_registration[0]
    else:
      registration = UserRegistration(lbw_id=lbw_id, user=request.user)
    user_registration_form = UserRegistrationForm(request.POST,
                                                  instance=registration)
    if user_registration_form.is_valid():
      user_registration_form.save()
      return HttpResponseRedirect(
          reverse('registration:detail', args=(lbw_id,)))
  else:
    try:
      user_registration = UserRegistration.objects.get(
          user__exact=request.user,
          lbw__exact=lbw)
      user_registration_form = UserRegistrationForm(
          instance=user_registration, lbw=lbw)
    except UserRegistration.DoesNotExist:
      user_registration_form = UserRegistrationForm(
          lbw=lbw,
          initial={'arrival_date': lbw.start_date,
                 'departure_date': lbw.end_date})
  return render(request, 'registration/register.html',
          {'lbw': lbw,
           'lbws': lbws,
           'user_registration_form': user_registration_form})

def activities(request, lbw_id):
  """Get all the activities for an LBW."""
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  return render(request, 'registration/activities.html',
                {'lbw': lbw, 'lbws': lbws})

def propose_activity(request, lbw_id):
  """Get all the activities for an LBW."""
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  if request.method == 'POST':
    instance = None
    if 'activity_id' in request.POST:
      instance = get_object_or_404(Activity, pk=request.POST['activity_id'])
    activity_form = ActivityForm(request.POST, instance=instance)
    if activity_form.is_valid():
      act = activity_form.save()
      if not instance:
        act.lbw = lbw
      if not act.owners.count():
        act.owners.add(request.user.lbwuser)
      if 'attachment' in request.FILES:
        act.attachment = request.FILES['attachment']
      act.save()
      if not instance and settings.LBW_TO_EMAIL:
        message = render_to_string('registration/new_activity.html',
                                   {'lbw': lbw, 'activity': act,
                                    'domain': request.get_host()})
        send_mail("New activity %s proposed for LBW %s" % (act.short_name,
                                                           lbw.short_name),
                  message, settings.LBW_FROM_EMAIL, settings.LBW_TO_EMAIL)
      return HttpResponseRedirect(reverse('registration:activities',
                                  args=(lbw_id,)))
    else:
      print 'activity_form is not valid'
  else:
    activity_form = ActivityForm()
  return render(request, 'registration/propose_activity.html',
                {'lbw': lbw, 'lbws': lbws, 'activity_form': activity_form})

def get_date_from_schedule_post(schedule_post):
  """Parse POST data to find a date."""
  try:
    if schedule_post['activity_day']:
      (month, day, year) = schedule_post['activity_day'].split('/')
      start_date = datetime.date(int(year), int(month), int(day))
      if schedule_post['activity_hour']:
        hour = int(schedule_post['activity_hour'])
        min = 0
        if schedule_post['activity_min']:
          min = int(schedule_post['activity_min'])
        start_time = datetime.time(hour, min, tzinfo=UTC())
      else:
        start_time = datetime.time(0, 0, tzinfo=UTC())
      return datetime.datetime.combine(start_date, start_time)
  except KeyError:
    return None

def activity(request, lbw_id, activity_id):
  """Print details for one activity."""
  act = get_object_or_404(Activity, pk=activity_id)
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  if lbw.id != act.lbw_id:
    raise Http404
  if request.method == 'POST':
    act.start_date = get_date_from_schedule_post(request.POST)
    act.save()
    return HttpResponseRedirect(reverse('registration:activities',
                                        args=(lbw_id,)))
  else:
    activity_form = ActivityForm(instance=act)
  return render(request, 'registration/activity.html',
                {'lbw': act.lbw, 'activity': act, 'lbws': lbws,
                 'activity_form': activity_form})

def activity_register(request, lbw_id, activity_id):
  """Toggle a user registration for an activity."""
  act = get_object_or_404(Activity, pk=activity_id)
  if lbw_id != act.lbw_id:
      raise Http404
  if request.user in act.attendees.all():
    act.attendees.remove(request.user)
  else:
    act.attendees.add(request.user)
  act.save()
  return HttpResponseRedirect(reverse('registration:activity',
                                      args=(activity_id,)))

def schedule(request, lbw_id):
  """Print out a schedule for an LBW."""
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  return render(
      request,
      'registration/schedule.html',
      {'lbw': lbw,
       'lbws': lbws})

def tshirts(request, lbw_id):
  """Nothing."""
  return HttpResponse("Showing tshirts for lbw %s." % lbw_id)

def rides(request, lbw_id):
  """Nothing."""
  return HttpResponse("Showing rides for lbw %s." % lbw_id)

def participants(request, lbw_id):
  """Print out everyone going to an LBW."""
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  return render(
      request,
      'registration/participants.html',
      {'lbw': lbw, 'lbws': lbws, 'users': lbw.userregistration_set.all()})

def message(request, lbw_id, message_id):
  """Read a message."""
  if not request.user.is_authenticated():
    return HttpResponseRedirect(reverse('registration:index'))
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  my_message = get_object_or_404(Message, pk=message_id)
  return render(request, 'registration/message.html',
                {'lbw': lbw, 'lbws': lbws, 'message': my_message})

def write_lbw_message(request, lbw_id):
  return write_message(request, lbw_id, None)

def write_activity_message(request, lbw_id, activity_id):
  return write_message(request, None, activity_id)

def write_message(request, lbw_id, activity_id=None):
  if not request.user.is_authenticated():
    return HttpResponseRedirect(reverse('registration:index'))
  lbws = Lbw.objects.order_by('-start_date')
  activity = None
  if activity_id:
    activity = get_object_or_404(Activity, pk=activity_id)
  if lbw_id:
    lbw = get_object_or_404(Lbw, pk=lbw_id)
  else:
    lbw = activity.lbw
  message_form = MessageForm()
  return render(request, 'registration/message_write.html',
                {'lbw': lbw, 'lbws': lbws, 'activity': activity,
                 'message_form': message_form})

def save_message(request, lbw_id):
  """Save a message."""
  if request.user.is_authenticated():
    if request.method == 'POST':
      base_message = Message(writer=request.user,
                             lbw_id=request.POST.get('lbw_id'),
                             activity_id=request.POST.get('activity_id', None))
      message_form = MessageForm(request.POST, instance=base_message)
      if message_form.is_valid():
        message = message_form.save()
        if message.activity_id:
          return HttpResponseRedirect(reverse('registration:activity',
                                              args=(message.activity_id,)))
        return HttpResponseRedirect(reverse('registration:detail',
                                            args=(message.lbw_id,)))
  return HttpResponseRedirect(reverse('registration:index'))

def reply_message(request, lbw_id, message_id):
  if request.user.is_authenticated():
    message = get_object_or_404(Message, pk=message_id)
    message_form = MessageForm()
    return render(request, 'registration/message_write.html',
		    {'lbw': message.lbw,
                     'lbws': lbws,
		     'activity': message.activity,
		     'message': message,
		     'message_form': message_form})
  return HttpResponseRedirect(reverse('registration:index'))

def delete_message(request, lbw_id, message_id):
  """Delete a message."""
  if request.is_ajax():
    try:
      message = get_object_or_404(Message, pk=message_id)
      if request.user == message.writer:
        message.delete()
        return HttpResponse('ok')
    except KeyError:
      return HttpResponse('incorrectly formatted request')
  else:
    raise Http404

def propose_lbw(request):
  """Propose an LBW."""
  lbws = Lbw.objects.order_by('-start_date')
  if request.method == 'POST':
    form = LbwForm(request.POST)
    if form.is_valid():
      lbw = form.save()
      if not lbw.owners.count():
        lbw.owners.add(request.user.lbwuser)
        lbw.save()
      if settings.LBW_TO_EMAIL:
          message = render_to_string('registration/new_lbw.html',
                                     {'lbw': lbw, 'domain': request.get_host()})
          send_mail("New LBW proposed: %s" % lbw.short_name, message,
                    settings.LBW_FROM_EMAIL, settings.LBW_TO_EMAIL)
      return HttpResponseRedirect(
          reverse('registration:detail', args=(lbw.id,)))
  else:
    form = LbwForm()
  return render(
      request,
      'registration/propose_lbw.html',
      {'lbws': lbws, 'form': form})

def delete_lbw(request, lbw_id):
  """Delete an LBW."""
  lbws = Lbw.objects.order_by('-start_date')
  if request.method == 'POST':
    form_lbw_id = request.POST['lbw_id']
    lbw = get_object_or_404(Lbw, pk=form_lbw_id)
    if request.user.lbwuser in lbw.owners.all():
      form = DeleteLbwForm(request.POST, instance=lbw)
      if form.is_valid():
        lbw.delete()
        return HttpResponseRedirect(
            reverse('registration:index'))
  else:
    lbw = get_object_or_404(Lbw, pk=lbw_id)
    if request.user.lbwuser in lbw.owners.all():
      form = DeleteLbwForm(instance=lbw)
      return render(
        request, 'registration/delete_lbw.html',
        {'lbws': lbws, 'form': form})
    else:
      return HttpResponseRedirect(
          reverse('registration:index'))

def update_lbw(request, lbw_id):
  """Update an LBW."""
  lbws = Lbw.objects.order_by('-start_date')
  if request.method == 'POST':
    form_lbw_id = request.POST['lbw_id']
    lbw = get_object_or_404(Lbw, pk=form_lbw_id)
    if request.user.lbwuser in lbw.owners.all():
      form = LbwForm(request.POST, instance=lbw)
      if form.is_valid():
        lbw = form.save()
        if not lbw.owners.count():
          lbw.owners.add(request.user.lbwuser)
          lbw.save()
        return HttpResponseRedirect(
            reverse('registration:detail', args=(lbw.id,)))
    else:
      return HttpResponseRedirect(
          reverse('registration:detail', args=(lbw.id,)))
  else:
    lbw = get_object_or_404(Lbw, pk=lbw_id)
    if request.user.lbwuser not in lbw.owners.all():
      return HttpResponseRedirect(
          reverse('registration:detail', args=(lbw.id,)))

    form = LbwForm(instance=lbw)
  return render(
      request, 'registration/propose_lbw.html',
      {'lbws': lbws, 'form': form})

def update_activity(request, lbw_id, activity_id):
  activity = get_object_or_404(Activity, pk=activity_id)
  lbws = Lbw.objects.order_by('-start_date')
  if lbw_id != activity.lbw_id:
    raise Http404
  activity_form = ActivityForm(instance=activity)
  return render(request, 'registration/propose_activity.html',
                {'lbw': activity.lbw, 'lbws': lbws, 'activity': activity,
                 'activity_form': activity_form})

def cancel_activity(request, lbw_id, activity_id):
  """Delete an activity."""
  if request.is_ajax():
    try:
      activity = get_object_or_404(Activity, pk=activity_id)
      if request.user.lbwuser in activity.owners.all():
        activity.delete()
        return HttpResponse('ok')
    except KeyError:
      return HttpResponse('incorrectly formatted request')
  else:
    raise Http404

def activity_attachment(request, lbw_id, activity_id):
  """Return the attachment for an activity."""
  activity = get_object_or_404(Activity, pk=activity_id)
  if lbw_id != activity.lbw_id:
    raise Http404
  if not activity.attachment:
    raise Http404
  return StreamingHttpResponse(activity.attachment.chunks())

def accommodation(request, lbw_id):
  lbw = get_object_or_404(Lbw, pk=lbw_id)
  lbws = Lbw.objects.order_by('-start_date')
  if request.method == 'POST':
    if request.user.is_authenticated():
      accommodation = Accommodation(lbw_id=lbw_id)
      form = AccommodationForm(request.POST, instance=accommodation)
      if form.is_valid():
        acc = form.save()
	acc.save()
  accommodation_form = AccommodationForm()
  return render(request, 'registration/accommodation.html',
          {'lbw': lbw, 'lbws': lbws, 'accommodation_form': accommodation_form})
