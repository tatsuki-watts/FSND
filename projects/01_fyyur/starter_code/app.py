#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from distutils.ccompiler import show_compilers
import json
from re import L
from this import d
from time import timezone
from dateutil.parser import parser
import babel
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_moment import Moment
from flask import Flask, g, render_template, request, Response, flash, redirect, url_for
from sqlalchemy import cast, func
from flask_migrate import Migrate
from models import db, Artist, Venue, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')
moment = Moment(app)
db.init_app(app)
migrate = Migrate(app, db, compare_type = True)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

# class Venue(db.Model):
#   __tablename__ = 'venues'
#   id = db.Column(db.Integer, primary_key=True)
#   name = db.Column(db.String)
#   city = db.Column(db.String(120))
#   state = db.Column(db.String(120))
#   address = db.Column(db.String(120))
#   phone = db.Column(db.String(120))
#   image_link = db.Column(db.String(500))
#   facebook_link = db.Column(db.String(120))
#   genres = db.Column(db.PickleType)
#   website = db.Column(db.String(120))
#   seeking_talent = db.Column(db.Boolean)
#   seeking_description = db.Column(db.String)
#   shows  = db.relationship('Show', backref='venue', lazy=True)
#   def __repr__(self):
#     return f'<venue id: {self.id}, name: {self.name}>'

# class Artist(db.Model):
#   __tablename__ = 'artists'
#   id = db.Column(db.Integer, primary_key=True)
#   name = db.Column(db.String)
#   city = db.Column(db.String(120))
#   state = db.Column(db.String(120))
#   phone = db.Column(db.String(120))
#   genres = db.Column(db.PickleType)
#   image_link = db.Column(db.String(500))
#   facebook_link = db.Column(db.String(120))
#   website = db.Column(db.String(120))
#   seeking_venue = db.Column(db.Boolean)
#   seeking_description = db.Column(db.String)
#   shows = db.relationship('Show', backref='artist', lazy=True)
#   def __repr__(self):
#     return f'<artist id: {self.id}, name: {self.name}>'

# class Show(db.Model):
#   __tablename__ = 'shows'
#   id = db.Column(db.Integer, primary_key=True)
#   artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable = False)
#   venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable = False)
#   start_time = db.Column(db.DateTime())
#   def __repr__(self):
#     return f'< show id: {self.id}, artist id: {self.artist_id}, venue id: {self.venue_id}, start time: {self.start_time}>'

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(date, format='medium'):
  #date = parser().parse(value, ignoretz=True) 
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#----------------------------------------------------------------------------#
#  Venues
#----------------------------------------------------------------------------#

@app.route('/venues')
def venues():
  data = []
  now = datetime.now(tz = None)
  locations = db.session.query(Venue.city, Venue.state).distinct()
  for location in locations:
    results = db.session.query(Venue.id, Venue.name, Venue.city, Venue.state, Venue.shows).\
      filter_by(city=location["city"], state=location["state"]).with_entities(Venue.id, Venue.name).\
      order_by(Venue.id)
    venues = []
    for venue in results:
      venues += [{
        'id': venue.id,
        'name': venue.name,
        'upcoming_shows': Show.query.filter(Show.venue_id == venue.id, Show.start_time > now).count() 
      }]
    data += [{
      "city": location.city,
      "state": location.state,
      "venues": venues
    }]
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term','')
  now = datetime.now()
  venues = db.session.query(Venue.id, Venue.name).filter(func.lower(Venue.name).contains(search_term.lower()))
  response = {
    "count": venues.count(),
    "data": [{**dict(venue),
      "num_upcoming_shows": Show.query.filter(Show.venue_id==venue.id, Show.start_time > now).count(),
    } for venue in venues.all()]
  }
  print(response)
  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  data = Venue.query.get(venue_id).__dict__
  showsAtVenue = Show.query.filter(Show.venue_id==venue_id)
  now = datetime.now()
  pastShows = showsAtVenue.filter(Show.start_time<now)
  upcomingShows = showsAtVenue.filter(Show.start_time>=now)
  data["past_shows"] = [{**show.__dict__,
    "artist_name": show.artist.name,
    "artist_image_link": show.artist.image_link} for show in pastShows.all()]
  data["past_shows_count"] = pastShows.count()
  data["upcoming_shows"] = [{
    **show.__dict__,
    "artist_name": show.artist.name,
    "artist_image_link": show.artist.image_link,
    } for show in upcomingShows.all()]
  data["upcoming_shows_count"] = upcomingShows.count()
  return render_template('pages/show_venue.html', venue=data)

#----------------------------------------------------------------------------#
#  Create Venue
#----------------------------------------------------------------------------#

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    form = VenueForm()
    venue = Venue(
      name = form.name.data, 
      city = form.city.data,
      state = form.state.data,
      address = form.address.data,
      phone = form.phone.data,
      genres = form.genres.data,
      image_link = form.image_link.data,
      facebook_link = form.facebook_link.data,
      website = form.website_link.data,
      seeking_talent = form.seeking_talent.data,
      seeking_description = form.seeking_description.data,
    )
    db.session.add(venue)
    db.session.commit()
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + form.name.data + ' could not be listed.')
  else:
    flash('Venue ' + form.name.data + ' was successfully listed!')
  finally:
    db.session.close()
  return render_template('pages/home.html')

@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    showsAtVenue = Show.query.filter_by(venue_id=venue_id).all()
    for show in showsAtVenue:
      db.session.delete(show)
    db.session.delete(venue)
    db.session.commit()
  except:
    db.session.rollback()
    flash(f'An error occurred. Venue {venue.name} could not be deleted.')
  else:
    flash(f'Venue {venue.name} was successfully deleted.')
  finally:
    db.session.close()
  return redirect(url_for('index'))


#----------------------------------------------------------------------------#
#  Artists
#----------------------------------------------------------------------------#

@app.route('/artists')
def artists():
  data = Artist.query.with_entities(Artist.id, Artist.name).order_by(Artist.id)
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  now = datetime.now()
  search_term=request.form.get('search_term', '')
  artists = db.session.query(Artist.id, Artist.name).filter(func.lower(Artist.name).contains(search_term.lower()))
  response = {
    "count": artists.count(),
    "data": [{**dict(artist),
      "num_upcoming_shows": Show.query.filter(Show.artist_id==artist.id, Show.start_time > now).count(),
      } for artist in artists.all()]
  }
  print(response)
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  data = Artist.query.get(artist_id).__dict__
  data["past_shows"] = []
  data["upcoming_shows"] = []
  results = Show.query.filter_by(artist_id=artist_id).all()
  show = {}
  now = datetime.now()
  for result in results:
    show["venue_id"] = result.venue_id
    show["venue_name"] = result.venue.name
    show["venue_image_link"] = result.venue.image_link
    show["start_time"] = result.start_time
    if result.start_time < now:
      data["past_shows"] += [dict(show)]
    else:
      data["upcoming_shows"] += [dict(show)]
  data["past_shows_count"] = len(data["past_shows"])
  data["upcoming_shows_count"] = len(data["upcoming_shows"])
  return render_template('pages/show_artist.html', artist = data)

#----------------------------------------------------------------------------#
#  Update
#----------------------------------------------------------------------------#

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.genres.data = artist.genres
  form.facebook_link.data = artist.facebook_link
  form.image_link.data = artist.image_link
  form.website_link.data = artist.website
  form.seeking_venue.data = artist.seeking_venue
  form.seeking_description.data = artist.seeking_description
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  form = ArtistForm()
  try: 
    artist = Artist.query.get(artist_id)
    artist.name = form.name.data
    artist.city = form.city.data
    artist.state = form.state.data
    artist.phone = form.phone.data
    artist.genres = form.genres.data
    artist.facebook_link = form.facebook_link.data
    artist.image_link = form.image_link.data
    artist.website = form.website_link.data
    artist.seeking_venue = form.seeking_venue.data
    artist.seeking_description = form.seeking_description.data
    db.session.commit()
  except: 
    db.session.rollback()
    flash(f'An error occurred. Artist {artist.name} could not be edited.')
  else:
    flash(f'Artist {artist.name} was successfully edited.')
  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.phone.data = venue.phone
  form.genres.data = venue.genres
  form.facebook_link.data = venue.facebook_link
  form.image_link.data = venue.image_link
  form.website_link.data = venue.website
  form.seeking_talent.data = venue.seeking_talent
  form.seeking_description.data = venue.seeking_description
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  try:
    venue.name = form.name.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.address = form.address.data
    venue.phone = form.phone.data
    venue.genres = form.genres.data
    venue.facebook_link = form.facebook_link.data
    venue.image_link = form.image_link.data
    venue.website = form.website_link.data
    venue.seeking_talent = form.seeking_talent.data
    venue.seeking_description = form.seeking_description.data
    db.session.commit()
  except:
    db.session.rollback()
    flash(f'An error occurred. Venue {venue.name} could not be edited.')
  else:
    flash(f'Venue {venue.name} was successfully edited.')
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#----------------------------------------------------------------------------#
#  Create Artist
#----------------------------------------------------------------------------#

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    form = ArtistForm()
    artist = Artist( 
      name = form.name.data,
      city = form.city.data,
      state = form.state.data,
      phone = form.phone.data,
      genres = form.genres.data,
      image_link = form.image_link.data,
      facebook_link = form.facebook_link.data,
      website = form.website_link.data,
      seeking_venue = form.seeking_venue.data,
      seeking_description = form.seeking_description.data,
    )
    db.session.add(artist)
    db.session.commit()
  except:
    db.session.rollback()
    flash('An error occurred. Artist ' + form.name.data + ' could not be listed.')
  else:
    flash('Artist ' + form.name.data + ' was successfully listed!')
  finally:
    db.session.close()

  return render_template('pages/home.html')

#----------------------------------------------------------------------------#
#  Shows
#----------------------------------------------------------------------------#

@app.route('/shows')
def shows():
  shows = []
  results = Show.query.all()
  for show in results:
    shows += [{
      "venue_id": show.venue_id,
      "venue_name": show.venue.name,
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      "start_time": show.start_time,
    }]
  return render_template('pages/shows.html', shows=shows)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  form = ShowForm()
  try:
    show = Show(
      artist_id = form.artist_id.data,
      venue_id = form.venue_id.data,
      start_time = form.start_time.data,
    )
    db.session.add(show)
    db.session.commit()
  except:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  else:
    flash('Show was successfully listed!')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
