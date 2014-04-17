/* ATTENTION: This file is created with mako and includes some attribute which
 * are inserted dynamically */

$('.formbar-tooltip').tooltip();
$('.formbar-datepicker').datepicker({
    format: 'yyyy-mm-dd',
    todayBtn: "linked",
});

/*
* Set hidden form field "formbar-page" to the value of the currently
* selected page. This value will be used to set the currently selected
* page when the form ist rendered
*/
$('div.formbar-form form div.tabbable ul.nav li a').click(function() {
  var page = $(this).attr('href').split('#p')[1];
  var item = $(this).attr('formbar-item');
  var itemid = $(this).attr('formbar-itemid');
  $.get('/set_current_form_page', 
        {
            page: page,
            item: item,
            itemid: itemid
        },
        function(data, status) {});
});

$('div.formbar-outline a').click(function() {
  var page = $(this).attr('href').split('#p')[1];
  var item = $(this).attr('formbar-item');
  var itemid = $(this).attr('formbar-itemid');
  $.get('/set_current_form_page', 
        {
            page: page,
            item: item,
            itemid: itemid
        },
        function(data, status) {});
  $('.formbar-page').hide();
  $('#formbar-page-'+page).show();
});
/*
 * Evaluate when values in the form changes
*/
evaluateFields();
evaluateConditionals();
$('div.formbar-form form input, div.formbar-form form select,  div.formbar-form form textarea').change(evaluateFields);
$('div.formbar-form form input, div.formbar-form form select,  div.formbar-form form textarea').change(evaluateConditionals);

function evaluate(element) {
    var expr = element['attributes'][0].value;
    var tokens = expr.split(" ");

    var form = $(element).closest("form");
    var eval_url = $(form).attr("evalurl"); 

    var eval_expr = "";
    // Build evaluation string
    for (var j = 0; j <= tokens.length - 1; j++) {
        var tfield = null;
        var value = null;
        if (tokens[j].contains("$")) {
            tfield = tokens[j].replace('$', '');
            // Select field
            var field = $('input[name='+tfield+'], '
                          + 'select[name='+tfield+'], '
                          + 'div[name='+tfield+'], '
                          + 'textarea[name='+tfield+']');
            value = field.val();
            // If we can not get a value from an input fields the field my
            // be readonly. So get the value from the readonly element.
            // First try to get the unexpaned value, if there is no
            // value get the textvalue of the field. (Which is usually
            // the expanded value).
            if (!value) {
                value = field.attr("value");
            }
            if (!value) {
                value = field.text();
            }
            console.log(tokens[j].replace('$', ''));
            eval_expr += " "+value;
        } else {
            eval_expr += " "+tokens[j];
        }
    }
    try {
        if (eval_url) {
            var result = false;
            $.ajax({
                type: "GET",
                async: false,
                url: eval_url,
                data: {rule: eval_expr},
                success: function (data) {
                    if (data.success) {
                        result = data.data;
                    } else {
                        console.log(data.params.msg);
                        result = data.data;
                    }
                },
                error: function (data) {
                    console.log("Request to eval server fails!");
                    result = false;
                }
            });
            return result;
        } else {
            return eval(eval_expr);
        }
    } catch (e) {
        console.log(e);
        return undefined;
    }
}

function evaluateConditionals() {
    var fieldsToEvaluate = $('.formbar-conditional');
    for (var i = fieldsToEvaluate.length - 1; i >= 0; i--) {
        var conditional = fieldsToEvaluate[i];
        var readonly = $(conditional).attr('class').contains('readonly');
        var result = evaluate(conditional);
        if (result) {
            if (readonly) {
                $(conditional).animate({opacity:'1.0'}, 1500);
                $(conditional).find('input, select, textarea').attr('readonly', false);
            }
            else {
                $(conditional).show();
            }
        }
        else {
            if (readonly) {
                $(conditional).animate({opacity:'0.4'}, 1500);
                $(conditional).find('input, select, textarea').attr('readonly', true);
            }
            else {
                $(conditional).hide();
            }
        }
    }
}

function evaluateFields() {
    var fieldsToEvaluate = $('.formbar-evaluate');
    for (var i = fieldsToEvaluate.length - 1; i >= 0; i--){
        var field = fieldsToEvaluate[i];
        var id = field['attributes'][1].value;
        var result = evaluate(field)
        if (result) {
            $('#'+id).text(result);
        }
        else {
            $('#'+id).text('NaN');
        }
    }
}