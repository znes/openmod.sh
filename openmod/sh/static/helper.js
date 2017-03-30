function alertModal(message, header = "", callback=function(){}) {
    $('.modal, .modal-backdrop').remove();
    $(document.body).append(
        '<div class="modal fade" id="alertModal" tabindex="-1" role="dialog" aria-labelledby="alertModalLabel" aria-hidden="true">'
        +'<div class="modal-dialog" role="document">'
            +'<div class="modal-content">'
            +'<div class="modal-header">'
                +'<h5 class="modal-title" id="alertModalLabel">' + header + '</h5>'
                +'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                +'<span aria-hidden="true">&times;</span>'
                +'</button>'
            +'</div>'
            +'<div class="modal-body">' + message + '</div>'
            +'<div class="modal-footer">'
                +'<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>'
            +'</div>'
            +'</div>'
        +'</div>'
        +'</div>');
    $('#alertModal').modal().show();
    $('#alertModal').on('hidden.bs.modal', function() {
        callback();
    });
}

function confirmModal(message, header = "", callback=function(){}) {
    $('.modal, .modal-backdrop').remove();
    $(document.body).append(
        '<div class="modal fade" id="confirmModal" tabindex="-1" role="dialog" aria-labelledby="conformModalLabel" aria-hidden="true">'
        +'<div class="modal-dialog" role="document">'
            +'<div class="modal-content">'
            +'<div class="modal-header">'
                +'<h5 class="modal-title" id="confirmModalLabel">' + header + '</h5>'
                +'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                +'<span aria-hidden="true">&times;</span>'
                +'</button>'
            +'</div>'
            +'<div class="modal-body">' + message + '</div>'
            +'<div class="modal-footer">'
                +'<button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>'
                +'<button type="button" class="btn btn-secondary confirm" data-dismiss="modal">OK</button>'
            +'</div>'
            +'</div>'
        +'</div>'
        +'</div>');
    $('#confirmModal').modal();
    $('#confirmModal').on('hidden.bs.modal', function(e) {
        callback(false);
    });
    $('#confirmModal .confirm').on('click', function(e) {
        $('#confirmModal').unbind( 'hidden.bs.modal');
        $('#confirmModal').modal('hide');
        $('#confirmModal').on('hidden.bs.modal', function(e) {
            callback(true);
        });
    });
}

function promptModal(text, defaultText="", header = "", callback=function(){}) {
    $('.modal, .modal-backdrop').remove();
    $(document.body).append(
        '<div class="modal fade" id="promptModal" tabindex="-1" role="dialog" aria-labelledby="promptModalLabel" aria-hidden="true">'
        +'<div class="modal-dialog" role="document">'
            +'<div class="modal-content">'
            +'<div class="modal-header">'
                +'<h5 class="modal-title" id="promptModalLabel">' + header + '</h5>'
                +'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                +'<span aria-hidden="true">&times;</span>'
                +'</button>'
            +'</div>'
            +'<div class="modal-body">' + text + '</div>'
                +'<div class="form-group">'
                    +'<input type="text" class="form-control" value="' + defaultText + '">'
                +'</div>'
            +'<div class="modal-footer">'
                +'<button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>'
                +'<button type="button" class="btn btn-secondary confirm" data-dismiss="modal">OK</button>'
            +'</div>'
            +'</div>'
        +'</div>'
        +'</div>');
    $('#promptModal').modal();
    $('#promptModal').on('hidden.bs.modal', function(e) {
        callback(null);
        return true;
    });
    $('#promptModal .confirm').on('click', function(e) {
        var inputValue = $('#promptModal').find('input').val();
        $('#promptModal').unbind( 'hide.bs.modal');
        $('#promptModal').modal('hide');
        $('#promptModal').on('hidden.bs.modal', function(e) {
            callback(inputValue);
        });
        return true;
    });
}
