# Create your views here.
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404
from fossbarcode.barcode.models import Product_Record, FOSS_Components, System_Settings, RecordForm, HeaderForm, ItemForm
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.conf import settings
from django.utils import simplejson as json

from fossbarcode import task

import sys, os, re, urllib, subprocess, time, datetime

# used to populate drop-downs for config options with fixed choices
CONFIG_CHOICES = (
    ('display_code_type', (
            ('128', 'Code 128 Barcode'),
            ('qr', 'QR Code with only the checksum, URL'),
            ('qr+', 'QR Code with BoM and oter data embedded in MECARD data'),
        )
    ),
)

# buffer size for Popen, we want unbuffered
bufsize = -1

### each of these views has a corresponding html page in ../templates/barcode

# task status page - intended for calling in javascript
def taskstatus(request):
    tm = task.TaskManager()
    return HttpResponse(tm.read_status())

# dynamically generate history.js file
def history_js(request):
    return render_to_response('media/js/history.js', { "idtag": 31337 },
                              mimetype="application/javascript")

# history - returns JSON, intended for calling from javascript
def history_json(request, record_id):
    p = Product_Record.objects.get(id=record_id)
    hist = [(x[0], datetime.date.fromtimestamp(x[1]).isoformat(), x[2])
            for x in p.iter_history()]
    return HttpResponse(json.dumps(hist), content_type="application/json")

# history_file - returns the file data for the path at revision
def history_file(request, record_id, revision, path):
    p = Product_Record.objects.get(id=record_id)
    repo = p.get_repo()
    traverse = repo.commit(revision).tree
    for path_component in os.path.split(path):
        traverse = repo.tree(traverse)[path_component][1]
    blob = repo.get_blob(traverse)
    return HttpResponse(blob.data, content_type="text/plain")

# system configuration settings
def sysconfig(request):
    info_message = ""

    if request.method == 'POST': # If the form has been submitted...
        # walk through all the known system settings and update
        # do we need to go back and regenerate all the QR codes if host_site changes?
        ss_list = System_Settings.objects.values('name')    
        for s in ss_list:
            ss_value = request.POST.get(s['name'], '')
            if (ss_value != ""):
                System_Settings.objects.filter(name = s['name']).update(value = ss_value, 
                                               last_updated = str(datetime.datetime.now()), 
                                               user_updated = True)

        return HttpResponseRedirect('/barcode/input/')

    else:
        # has the user confirmed the settings?
        settings_done = System_Settings.objects.filter(user_updated = True).count()
        if (settings_done) == 0:
            info_message = "You must confirm and save the system settings to continue..."
        
    settings_list = System_Settings.objects.order_by('name')
    host_site = get_config_value('host_site')

    return render_to_response('barcode/sysconfig.html', {'info_message': info_message,
                                                        'settings_list': settings_list,
                                                        'host_site': host_site, 'config_choices': CONFIG_CHOICES,
                                                        'tab_sysconfig': True })

# record detail page - this is a multiform too with the edit additions
def detail(request, record_id, revision=None):
    error_message = ''
    old_spdx = ''
    enable_edits = True
    foss = render_detail(record_id, revision)
    record_list = Product_Record.objects.filter(id = record_id)
    if record_list.count() != 0:
        record = record_list[0]
    else:
        record = ''
        error_message = "No data for record " + record_id
        enable_edits = False

    # gather some config values we need
    host_site = get_config_value('host_site')
    display_code_type = get_config_value('display_code_type')

    # Create the history.
    record_history = []
    if record:
        for (commit, commit_time, msg) in record.iter_history():
            record_history.append((commit, datetime.date.fromtimestamp(commit_time), msg))

    if request.method == 'POST': # If the form has been submitted...
        mode = urllib.unquote(request.POST.get('submit'))

        headerform = HeaderForm(request.POST) # A form bound to the POST data
        itemform = ItemForm(request.POST) # A form bound to the POST data

        if (mode == "Clone Record"):
            if headerform.is_valid(): # All validation rules pass            
                pr = Product_Record.objects.get(id = record_id)
                try:
                    newpr = pr.clone( company=request.POST.get('company', ''),
                                      product = request.POST.get('product', ''), 
                                      version = request.POST.get('version', ''),
                                      release = request.POST.get('release', ''))
                    record_id = str(newpr.id)
                except:
                    error_message += "Record clone failed..."

        if (mode == "Update Header"):
            if headerform.is_valid(): # All validation rules pass            
                Product_Record.objects.filter(id = record_id).update(company = request.POST.get('company', ''),
                                                                 website = request.POST.get('website', ''),
                                                                 product = request.POST.get('product', ''),
                                                                 version = request.POST.get('version', ''),
                                                                 release = request.POST.get('release', ''),
                                                                 contact = request.POST.get('contact', ''),
                                                                 email = request.POST.get('email', ''),
                                                                 record_date = str(datetime.datetime.now()))

                # compute the new checksum, compare with the old and update if needed
                pr = Product_Record.objects.get(id = record_id)
                checksum = pr.checksum
                new_checksum = pr.calc_checksum()
                if checksum != new_checksum:
                    pr.checksum = new_checksum
                    pr.save()
                    result = pr.checksum_to_barcode()
                    for extension in (".png", ".ps"):
                        try:
                            pr.delete_file(checksum + extension)
                        except:
                            error_message += "Failed to delete: " + checksum + extension + "<br>"
                    
                # now we generate all types, so regen always
                result = pr.checksum_to_barcode()              
                  
                # commit changes to version control
                pr.commit(request.POST.get('header_commit_message', ''))
 
            else:
                error_message += "Invalid header update data, see header dialog..."

        if (mode == "Clone Record" or mode == "Update Header"):
            if (error_message == ''):
                return HttpResponseRedirect('/barcode/' + record_id + '/detail/') 

        if (mode == "Update Item" or mode == "Add Item" or mode == "Delete Item"):
            if itemform.is_valid() or mode == "Delete Item": # All validation rules pass, or we're deleting
 
                # needed for file/change control operations below
                pr = Product_Record.objects.get(id = record_id)

                new_spdx = request.POST.get('foss_spdx', '')
                if (mode == "Update Item" or mode == "Delete Item"):               
                    foss_id = request.POST.get('foss_record_id', '')
                    fd = FOSS_Components.objects.get(brecord = record_id, id = foss_id)
                    old_spdx = fd.spdx_file

                elif (mode == "Add Item"):
                    fd = FOSS_Components(brecord_id = record_id, 
                                         package = request.POST.get('foss_component', ''),
                                         version = request.POST.get('foss_version', ''),
                                         copyright = request.POST.get('foss_copyright', ''), 
                                         attribution = request.POST.get('foss_attribution', ''),
                                         license = request.POST.get('foss_license', ''), 
                                         license_url = request.POST.get('foss_license_url', ''), 
                                         url = request.POST.get('foss_url', ''), 
                                         spdx_file = os.path.basename(new_spdx))

                    fd.save()
                    foss_id = fd.id
                else:
                    error_message += "Unknown request made<br>"

                if (mode == "Update Item"):
                    # line item data is in a file, so we alter/save rather than update
                    fd.package = request.POST.get('foss_component', '')
                    fd.version = request.POST.get('foss_version', '')
                    fd.copyright = request.POST.get('foss_copyright', '')
                    fd.attribution = request.POST.get('foss_attribution', '')
                    fd.license = request.POST.get('foss_license', '')
                    fd.license_url = request.POST.get('foss_license_url', '')
                    fd.url = request.POST.get('foss_url', '')
                    fd.spdx_file = os.path.basename(new_spdx)
                
                if (mode == "Delete Item"):
                    fd.delete()

                # save and/or delete SPDX file if there's a change
                if old_spdx != os.path.basename(new_spdx):
                    if new_spdx != '':
                        try:
                            pr.new_file_from_existing(new_spdx, "spdx_files")
                        except:
                            error_message += "Failed to copy spdx file:" + new_spdx + "<br>"

                    if old_spdx != '':
                        try:
                            pr.delete_file("spdx_files/" + old_spdx)
                        except:
                            error_message += "Failed to delete: " + old_spdx + "<br>"

                # update/save/del patches
                patch_files = request.POST.get('foss_patches', '')
                if patch_files != '':
                    patches = patch_files.split("\r\n")

                    # remove patches no longer listed 
                    old_patches = [x for x in fd.patch_files
                                   if x not in patches]
                    for p in old_patches:
                        try:
                            pr.delete_file("patches/" + p)
                        except:
                            error_message += "Failed to delete: " + p + "<br>"
                        fd.patch_files.remove(p)

                    # and add any new ones
                    for patch in patches:
                        if patch != '' and patch not in fd.patch_files:
                            try:
                                pr.new_file_from_existing(patch, "patches")
                                fd.patch_files.append(os.path.basename(patch))
                            except:
                                error_message += "Failed to copy patch file: " + str(patch) + "<br>"

                else:
                    # no patches specified, remove any that might be present
                    if (mode != "Add Item"):
                        for patch in fd.patch_files:
                            try:
                                pr.delete_file("patches/" + patch)
                            except:
                                error_message += "Failed to delete: " + patch + "<br>"
                        fd.patch_files = []

                # save changes to component
                if mode not in ["Delete Item", "Add Item"]:
                    fd.save()

                # update the master record "last updated"         
                pr.record_date = datetime.datetime.now()
                pr.save()
                
                # QR+ code changes with any change (record_date, components)
                result = pr.checksum_to_barcode()              

                # commit changes to version control
                if (mode == "Delete Item"):
                    pr.commit('Delete line item record for "' + fd.package + '"' )
                else:
                    pr.commit(request.POST.get('item_commit_message', ''))

                # back to the page, with a clean slate and any error messages, we need to re-render to pickup changes
                foss = render_detail(record_id)
                record_list = Product_Record.objects.filter(id = record_id)
                record = record_list[0]

            else:
                error_message = "Invalid line item update data, see item dialog..."

    headerform = HeaderForm() # An unbound form
    itemform = ItemForm() # An unbound form

    return render_to_response('barcode/detail.html', {'record': record, 'foss': foss, 'history': record_history,
                                                      'host_site': host_site, 'tab_results': True, 'revision': revision,
                                                      'error_message': error_message, 'enable_edits': enable_edits,
                                                      'display_code': display_code_type,
                                                      'headerform': headerform, 'itemform': itemform })

# record search page
def search(request):
    error_message = ""
    if request.method == 'POST': # If the form has been submitted...
        searchsum = request.POST.get('searchsum', '')
        record_list = Product_Record.objects.filter(checksum = searchsum)
        if record_list.count() == 0:
            error_message = "Record not found..."
        else:
            id = record_list[0].id
            return HttpResponseRedirect('/barcode/' + str(id) + '/detail/')

    return render_to_response('barcode/search.html', {'error_message': error_message, 'tab_search': True})

# used to see if user is entering a duplicate record in the input tab, no search_dupes.html
def search_dupes(request):
    scompany = request.GET.get('company', '')
    sproduct = request.GET.get('product', '')
    sversion = request.GET.get('version', '')
    srelease = request.GET.get('release', '')
    record_list = Product_Record.objects.filter(company = scompany, product = sproduct, version = sversion, release = srelease)
    if record_list.count() == 0:
        r = "None"
    else:
        r = record_list[0].id
    
    return HttpResponse(''.join(str(r)))
 
# record list page - this is also a form, for record deletions
def records(request):
    error_message = ''
    if request.method == 'POST': # If the form has been submitted...
        recordlist = request.POST.get('recordlist', '')
        if recordlist != '':
            records = recordlist.split(",")

            # delete all the selected records from the database
            for record in records:
                if record != '':
                    error_message = delete_record(record)

    rendered = []
    himage = '<img src="/site_media/images/filetree/code.png" title="Change History">'
    liclose = "</ul></li>"
    ctr = 1

    # pre-render the outline display for speed, uses mktree.js for a collapsible list
    companies = Product_Record.objects.values_list('company').distinct()
    if companies.count() != 0:
        for c in companies:
            # use <li class="liOpen"> to force open state
            rendered.append("<li><b>" + c[0] + ":</b><ul>")
            products = Product_Record.objects.values_list('product').filter(company = c[0]).distinct()
            for p in products:
                rendered.append("<li>" + p[0] + ":<ul>")
                versions = Product_Record.objects.values_list('version').filter(company = c[0], product = p[0]).distinct()
                for v in versions:
                    rendered.append("<li>Version " + v[0] + ":<ul>")
                    releases = Product_Record.objects.filter(company = c[0], product = p[0], version = v[0])
                    if releases.count() != 0:
                        rendered.append('<table border="1" cellpadding="5" width="900px">')
                        for r in releases:
                            recid = str(r.id)
                            rendered.append('<tr>')
                            rendered.append('<td width="45" valign="center"><input type="checkbox" name="recordcheck" value="' + recid + '">')
                            rendered.append('<span id="history-modal">')
                            rendered.append('<a href="#" class="basic" name="history' + str(ctr) +'"')
                            rendered.append('id="' + recid + '">' + himage + '</a>')
                            rendered.append('</span></td>')
                            rendered.append('<td><a href="/barcode/' + recid + '/detail/">Release ' + r.release + '</a></td>')
                            rendered.append('<td><a href="' + r.website + '" target="_blank">' + r.website + '</a></td>')
                            rendered.append('<td><a href="mailto:' + r.email + '" target="_blank">' + r.email + '</a></td>')
                            rendered.append('<td>' + r.contact + '</td>')
                            rendered.append('<td>' + r.record_date.strftime("%m/%d/%Y %I:%m %p") + '</td>')
                            rendered.append('</tr>')
                            ctr += 1
                        rendered.append('</table>')
                    rendered.append(liclose)
                rendered.append(liclose)
            rendered.append(liclose)
    
    return render_to_response('barcode/records.html', {'rendered_list': rendered,
                                                       'error_message': error_message, 
                                                       'tab_records': True })

# input form - this is where the real work happens
def input(request):

    error_message = check_for_system_apps()
    foss_components = ''
    foss_versions = ''
    foss_copyrights = ''
    foss_attributions = ''
    foss_licenses = ''
    foss_license_urls = ''
    foss_urls = ''
    foss_spdxs = ''
    foss_patches = ''
    component_error = ''
    needs_setup = 0

    # we don't do anything with this content, just used to format the modal popup
    # because it's also a subset of Recordform, change out the id string id_foo -> id_m_foo
    itemform = ItemForm(auto_id='id_m_%s') # An unbound form

    if request.method == 'POST': # If the form has been submitted...
        recordform = RecordForm(request.POST) # A form bound to the POST data      
 
        # we need these whether it's valid or not to repopulate on a bad submit        
        foss_components = request.POST.get('foss_components', '')
        foss_versions = request.POST.get('foss_versions', '')
        foss_copyrights = request.POST.get('foss_copyrights', '')
        foss_attributions = request.POST.get('foss_attributions', '')
        foss_licenses = request.POST.get('foss_licenses', '')
        foss_license_urls = request.POST.get('foss_license_urls', '')
        foss_urls = request.POST.get('foss_urls', '')
        foss_spdxs = request.POST.get('foss_spdxs', '')

        # need at least one full component entry to proceed
        if foss_components == '' or foss_versions == '' or foss_copyrights == '' \
          or foss_attributions == '' or foss_licenses == '' or foss_license_urls == '' or foss_urls == '':
            component_error = "At least one full component record is required...<br>"
  
        # patches are each in their own text area
        if foss_components != '':
            components = foss_components.split(",")
            for i in range(0, len(components)-1):
                foss_patches += request.POST.get('foss_patches' + str(i), '') + ","

        # back to "normal" processing
        if recordform.is_valid() and component_error == '': # All validation rules pass
            recorddata = recordform.save(commit=False)       
            recorddata.save()
  
            recordid = recorddata.id
            data_dest = recorddata.file_path()
            if not recorddata.setup_directory():
                error_message += "Failed to create " + data_dest + "<br>"
            
            spdx_dest = os.path.join(data_dest, "spdx_files")
            patch_dest = os.path.join(data_dest, "patches")

            # if we have foss components, store them also, and the patches
            if foss_components != '':
                components = foss_components.split(",")
                versions = foss_versions.split(",")
                copyrights = foss_copyrights.split(",")
                attributions = foss_attributions.split(",")
                licenses = foss_licenses.split(",")
                license_urls = foss_license_urls.split(",")
                urls = foss_urls.split(",")
                spdxs = foss_spdxs.split(",")

                i = 0
                for foss in components:
                    if foss != "":
                        fossdata = FOSS_Components(brecord_id = recordid, 
                                                   package = foss, version = versions[i],
                                                   copyright = copyrights[i], attribution = attributions[i],
                                                   license = licenses[i], license_url = license_urls[i], 
                                                   url = urls[i], spdx_file = os.path.basename(spdxs[i]))

                        # check for SPDX files and save in user_data
                        if spdxs[i] != '':
                            try:
                                recorddata.new_file_from_existing(spdxs[i], "spdx_files")
                            except:
                                error_message += "Failed to copy " + str(spdxs[i]) + "to " + spdx_dest + "<br>"

                        # check for patches and save in user_data
                        patch_files = request.POST.get('foss_patches' + str(i), '')
                        if patch_files != "":
                            patches = patch_files.split("\n")
                            for patch in patches:
                                patch = patch[:-1]
                                if patch != "":
                                    try:
                                        recorddata.new_file_from_existing(patch, "patches")
                                        fossdata.patch_files.append(os.path.basename(patch))
                                    except:
                                        error_message += "Failed to copy " + str(patch) + "to " + patch_dest + "<br>"

                        # save information after everything's collected
                        fossdata.save()
                        fossid = fossdata.id

                    i = i + 1

            # generate the checksum/barcode
            checksum = recorddata.calc_checksum()

            if checksum:
                recorddata.checksum = checksum
                recorddata.save()
                result = recorddata.checksum_to_barcode()
                if result:
                    error_message += "Barcode generation failed...<br>"
            else:
                error_message += "Checksum generation failed...<br>"

            # Commit the whole thing to version control
            recorddata.commit("Created new record from form.")

            if error_message == '':
                return HttpResponseRedirect('/barcode/' + str(recordid) + '/detail/')

        else:
            error_message = recordform.errors
    else:
        recordform = RecordForm() # An unbound form
        
        # check if the user has done basic setup
        settings_done = System_Settings.objects.filter(user_updated = True).count()
        if (settings_done) == 0:
            error_message = 'Please Configure Basic System Settings <a href="/barcode/sysconfig/">Here</a>'
            needs_setup = 1

    return render_to_response('barcode/input.html', {
                              'error_message': error_message, 'component_error': component_error, 
                              'recordform': recordform, 'itemform': itemform, 'needs_setup': needs_setup,
                              'foss_components': foss_components, 'foss_versions': foss_versions,
                              'foss_copyrights': foss_copyrights, 'foss_attributions': foss_attributions,
                              'foss_licenses': foss_licenses, 'foss_license_urls': foss_license_urls, 
                              'foss_urls': foss_urls, 'foss_spdxs': foss_spdxs,
                              'foss_patches': foss_patches, 'tab_input': True })

### these are all basically documentation support

# doc page
def documentation(request):
    from site_settings import gui_name, gui_version

    # Read the standalone docs, and reformat for the gui
    docs = ''
    status = 0

    try:
        f = open(settings.STATIC_DOC_ROOT + "/docs/index.khtml", 'r')

    except:
        # docs aren't created yet, try to do it
        status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && make")
        if status != 0:
            status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && ./text-docs-to-html > index.html.addons")
            if status == 0:
                status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && cat index.html.base index.html.addons index.html.footer > index.html")
            else:
                docs = "<b>Error, no index.html in fossbarcode/media/docs.</b><br>"
                docs += "If working with a git checkout or tarball, please type 'make' in the top level directory.<br>"
                docs += "</body>"

    # something worked above
    if not docs:
        f = open(settings.STATIC_DOC_ROOT + "/docs/index.html", 'r')
        doc_index = []
        for line in f:
            #replace the div styles for embedded use
            line = line.replace('<div id="lside">', '<div id="lside_e">')
            line = line.replace('<div id="main">', '<div id="main_e">')
            line = line.replace('<img src="', '<img src="/site_media/docs/')
            doc_index.append(line)
        f.close()
    
        # drop the first 11 lines
        docs = ''.join(doc_index[11:])

    return render_to_response('barcode/documentation.html', 
                              {'name': gui_name, 
                               'version': gui_version, 
                               'gui_docs': docs })

# this does not have a corresponding dirlist.html
# this is dynamic filetree content fed to jqueryFileTree for the input.html file/dir selection
# script for jqueryFileTree points to /barcode/dirlist/
def dirlist(request):
    # filter out some directories that aren't useful from "/"
    not_wanted = [ '/proc', '/dev', '/sys', '/initrd' ]
    r=['<ul class="jqueryFileTree" style="display: none;">']
    try:
        d=urllib.unquote(request.POST.get('dir'))
        content = os.listdir(d)
        # slows things a little, but looks more like 'ls'
        for f in sorted(content, key=unicode.lower):
            ff=os.path.join(d,f)
            if ff not in not_wanted and f != 'lost+found':
                if os.path.isdir(ff): 
                    r.append('<li class="directory collapsed"><a href="#" rel="%s/">%s</a></li>' % (ff,f))
                else:
                    e=os.path.splitext(f)[1][1:] # get .ext and remove dot
                    r.append('<li class="file ext_%s"><a href="#" rel="%s">%s</a></li>' % (e,ff,f))
        r.append('</ul>')
    except Exception,e:
        r.append('Could not load directory: %s' % str(e))
    r.append('</ul>')
    return HttpResponse(''.join(r))

### utility functions

# check for the system utilities we need
# FIXME - what if "which" isn't present?
def check_for_system_apps():
    errmsg = ''
    apps_needed = ['barcode', 'qrencode' , 'pstopnm', 'pnmtopng', 'sam2p']
    for app in apps_needed:
        result = os.system("which " + app + "> /dev/null")
        if result:
            errmsg += "Could not find system app '<i>" + app + "</i>'...<br>"
            if app == "barcode" or app == "qrencode":
                errmsg += "(See the documentation for building '<i>" + app + "</i>' from source)<br>"

    if errmsg:
        errmsg += "Application will fail to generate qr/barcode images without these apps<br>"
        errmsg += "Please use your system package manager to install them<br>"

    return errmsg

# to remove a record
def delete_record(recid):
    errmsg = ''
    q = Product_Record.objects.filter(id = recid)
    checksum = q[0].checksum
    try:
        q[0].remove_directory()
    except:
        errmsg += "Failed to delete user data...<br>"
    q.delete()
    return errmsg

# delete table records requested by id from one of the input forms
def delete_records(table, rlist):
            
    records = rlist.split(",")

    for record in records:
        if record != '':
            q = table.objects.filter(id = record)
            q.delete()

# pre-render some of the record detail
def render_detail(id, revision=None):
    media_root = '<a href="/site_media/user_data/'
    history_root = '<a href="/barcode/'
    foss = []
    foss_list = FOSS_Components.objects.filter(brecord = id)
    for f in foss_list:
        if revision:
            f.switch_revision(revision)
        fossid = f.id
        if f.spdx_file != '':
            spdx_file = media_root + str(id) + "/spdx_files/" + os.path.basename(f.spdx_file) + '">' + f.spdx_file + "</a><br>"
        else:
            spdx_file = ''

        patches = ""
        if revision:
            for p in f.patch_files:
                patches += history_root + str(id) + "/detail/" + revision + "/patches/" + os.path.basename(p) + '">' + p + "</a><br>"
        else:
            for p in f.patch_files:
                patches += media_root + str(id) + "/patches/" + os.path.basename(p) + '">' + p + "</a><br>"
        foss.append({'id': f.id, 'component': f.package, 'version': f.version, 
                     'copyright': f.copyright, 'attribution': f.attribution, 
                     'license': f.license, 'license_url': f.license_url, 
                     'url': f.url, 'spdx_file': spdx_file, 'patches': patches})
    return foss

# get a system configuration value
def get_config_value(cname):
    settings_list = System_Settings.objects.filter(name = cname)
    if settings_list:
        return settings_list[0].value
    else:
        return false


