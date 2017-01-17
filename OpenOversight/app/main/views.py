import datetime
import os
from flask import (abort, render_template, request, redirect, url_for,
                   send_from_directory, flash, session, current_app)
from flask_login import (LoginManager, login_user, logout_user,
                         current_user, login_required)
from functools import wraps
import tempfile
from werkzeug import secure_filename

from . import main
from ..utils import (grab_officers, roster_lookup, upload_file, compute_hash,
                     serve_image, compute_leaderboard_stats)
from .forms import FindOfficerForm, FindOfficerIDForm, HumintContribution
from ..models import db, Image, User, Face

# Ensure the file is read/write by the creator only
SAVED_UMASK = os.umask(0077)


def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_administrator:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@main.route('/')
@main.route('/index')
def index():
    return render_template('index.html')


@main.route('/find', methods=['GET', 'POST'])
def get_officer():
    form = FindOfficerForm()
    if form.validate_on_submit():
        return redirect(url_for('main.get_gallery'), code=307)
    return render_template('input_find_officer.html', form=form)


@main.route('/label', methods=['GET', 'POST'])
def get_started_labeling():
    return render_template('label_data.html')


@main.route('/sort', methods=['GET', 'POST'])
@login_required
def sort_images():
    # Select a random unsorted image from the database
    image = Image.query.filter_by(contains_cops=None).first()
    if image:
        proper_path = serve_image(image.filepath)
    else:
        proper_path = None
    return render_template('sort.html', image=image, path=proper_path)


@main.route('/tutorial')
def get_tutorial():
    return render_template('tutorial.html')


@main.route('/user/<username>')
def profile(username):
    try:
        user = User.query.filter_by(username=username).one()
    except:
        abort(404)
    return render_template('profile.html', user=user)


@main.route('/user/<username>/<int:toggle>')
@admin_required
def toggle_user(username, toggle):
    try:
        user = User.query.filter_by(username=username).one()
        if toggle == 1:
            user.is_disabled = True
        elif toggle == 0:
            user.is_disabled = False
        db.session.commit()
        flash('Updated user status')
    except:
        flash('Unknown error occurred')
    return redirect(url_for('main.profile', username=username))


@main.route('/image/<int:image_id>')
@login_required
def display_submission(image_id):
    try:
        image = Image.query.filter_by(id=image_id).one()
        proper_path = serve_image(image.filepath)
    except:
        abort(404)
    return render_template('image.html', image=image, path=proper_path)


@main.route('/tag/<int:tag_id>')
@login_required
def display_tag(tag_id):
    try:
        tag = Face.query.filter_by(id=tag_id).one()
        proper_path = serve_image(tag.image.filepath)
    except:
        abort(404)
    return render_template('tag.html', face=tag, path=proper_path)


# Rate limiting / CAPTCHA needed on this route
@main.route('/image/classify/<int:image_id>/<int:contains_cops>')
@login_required
def classify_submission(image_id, contains_cops):
    try:
        image = Image.query.filter_by(id=image_id).one()
        image.user_id = current_user.id
        if contains_cops == 1:
            image.contains_cops = True
        elif contains_cops == 0:
            image.contains_cops = False
        db.session.commit()
        flash('Updated image classification')
    except:
        flash('Unknown error occurred')
    return redirect(redirect_url())
    #return redirect(url_for('main.display_submission', image_id=image_id))


@main.route('/tag/delete/<int:tag_id>')
@admin_required
def delete_tag(tag_id):
    try:
        tag = Face.query.filter_by(id=tag_id).delete()
        db.session.commit()
        flash('Deleted this tag')
    except:
        flash('Unknown error occurred')
    return redirect(url_for('main.index'))


# Rate limiting / CAPTCHA needed on this route
@main.route('/tag/add/<int:officer_id>/<int:image_id>')
@login_required
def add_tag(tag_id):
    try:
        image = Image.query.filter_by(id=image_id).one()
        image.user_id = current_user.id
        # Should be done in form
        db.session.commit()
        #tag_id = Face.query.filter_by(image_id=image_id) \
        #                   .filter_by(officer_id=officer_id).one()
        flash('Tag added to database')
        #return redirect(url_for('main.display_tag', tag_id=tag_id))
    except:
        flash('Unknown error occurred')
    return redirect(url_for('main.index'))


@main.route('/leaderboard')
def leaderboard():
    top_sorters, top_taggers = compute_leaderboard_stats()
    return render_template('leaderboard.html', top_sorters=top_sorters,
                           top_taggers=top_taggers)


@main.route('/cop_face', methods=['GET', 'POST'])
@login_required
def label_data():
    # Select a random untagged image from the database
    image = Image.query.filter_by(contains_cops=True) \
                       .filter_by(is_tagged=False).first()
    if image:
        proper_path = serve_image(image.filepath)
    else:
        proper_path = None
    return render_template('cop_face.html', image=image, path=proper_path)






# Rate limiting / CAPTCHA on this route
@main.route('/image/tagged/<int:image_id>')
@login_required
def complete_tagging(image_id):
    # Select a random untagged image from the database
    image = Image.query.filter_by(id=image_id).one()
    image.is_tagged = True
    db.session.commit()
    flash('Marked image as completed.')
    return redirect(url_for('main.label_data'))


@main.route('/tagger_gallery/<int:page>', methods=['GET', 'POST'])
@main.route('/tagger_gallery', methods=['GET', 'POST'])
def get_tagger_gallery(page=1):
    form = FindOfficerIDForm()
    if form.validate_on_submit():
        OFFICERS_PER_PAGE = int(current_app.config['OFFICERS_PER_PAGE'])
        form_data = form.data
        officers = roster_lookup(form_data).paginate(page, OFFICERS_PER_PAGE, False)
        return render_template('tagger_gallery.html',
                               officers=officers,
                               form=form,
                               form_data=form_data)
    else:
        return redirect(url_for('main.label_data'), code=307)


@main.route('/gallery/<int:page>', methods=['GET', 'POST'])
@main.route('/gallery', methods=['GET','POST'])
def get_gallery(page=1):
    form = FindOfficerForm()
    if form.validate_on_submit():
        OFFICERS_PER_PAGE = int(current_app.config['OFFICERS_PER_PAGE'])
        form_data = form.data
        officers = grab_officers(form_data).paginate(page, OFFICERS_PER_PAGE, False)
        return render_template('gallery.html',
                               officers=officers,
                               form=form,
                               form_data=form_data)
    else:
        return redirect(url_for('main.get_officer'))


@main.route('/complaint', methods=['GET', 'POST'])
def submit_complaint():
    return render_template('complaint.html',
                           officer_first_name=request.args.get('officer_first_name'),
                           officer_last_name=request.args.get('officer_last_name'),
                           officer_middle_initial=request.args.get('officer_middle_name'),
                           officer_star=request.args.get('officer_star'),
                           officer_image=request.args.get('officer_image'))


@main.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_data():
    form = HumintContribution()
    if request.method == 'POST' and form.validate_on_submit():
        original_filename = secure_filename(request.files[form.photo.name].filename)
        image_data = request.files[form.photo.name].read()

        # See if there is a matching photo already in the db
        hash_img = compute_hash(image_data)
        hash_found = Image.query.filter_by(hash_img=hash_img).first()

        if not hash_found:
            # Generate new filename
            file_extension = original_filename.split('.')[-1]
            new_filename = '{}.{}'.format(hash_img, file_extension)

            # Save temporarily on local filesystem
            tmpdir = tempfile.mkdtemp()
            safe_local_path = os.path.join(tmpdir, new_filename)
            with open(safe_local_path, 'w') as tmp:
                tmp.write(image_data)
            os.umask(SAVED_UMASK)

            # Upload file from local filesystem to S3 bucket and delete locally
            try:
                 url = upload_file(safe_local_path, original_filename,
                                   new_filename)
                 # Update the database to add the image
                 new_image = Image(filepath=url, hash_img=hash_img, is_tagged=False,
                                   date_image_inserted=datetime.datetime.now(),
                                   # TODO: Get the following field from exif data
                                   date_image_taken=datetime.datetime.now())
                 db.session.add(new_image)
                 db.session.commit()

                 flash('File {} successfully uploaded!'.format(original_filename))
            except:
                flash("Your file could not be uploaded at this time due to a server problem. Please retry again later.")
            os.remove(safe_local_path)
            os.rmdir(tmpdir)
        else:
            flash('This photograph has already been uploaded to OpenOversight.')
    elif request.method == 'POST':
        flash('File unable to be uploaded. Try again...')
    return render_template('submit.html', form=form)


@main.route('/about')
def about_oo():
    return render_template('about.html')


@main.route('/contact')
def contact_oo():
    return render_template('contact.html')


@main.route('/privacy')
def privacy_oo():
    return render_template('privacy.html')


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'
