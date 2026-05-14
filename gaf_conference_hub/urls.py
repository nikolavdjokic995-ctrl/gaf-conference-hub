from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from conferences.views import (
    home,
    register,
    conference_overview,
    edit_conference_overview,
    conference_settings,
    edit_submission_settings,
    email_templates,
    edit_email_template,
    preview_email_template,
    submit_paper,
    important_information,
    add_info_card,
    edit_info_card,
    delete_info_card,
    add_sidebar_card,
    edit_sidebar_card,
    delete_sidebar_card,
    conference_topics,
    add_conference_topic,
    edit_conference_topic,
    delete_conference_topic,
    assign_papers,
    conference_submissions,
    conference_people,
    my_reviews,
    review_submission,
    download_review_paper,
    submission_result,
    manager_dashboard,
    make_decision,
    judge_dashboard,
    my_submissions,
    delete_submission,
    reviewer_dashboard,
    upload_revision,
    send_revision_to_reviewers,
    layout_dashboard,
    layout_decision,
    footer_settings,
    footer_settings,
    add_footer_partner,
    edit_footer_partner,
    delete_footer_partner,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    path("login/", auth_views.LoginView.as_view(
        template_name="conferences/login.html"
    ), name="login"),

    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("register/", register, name="register"),

    path("dashboard/", manager_dashboard, name="dashboard"),
    path("judge-dashboard/", judge_dashboard, name="judge_dashboard"),
    path("reviewer-dashboard/", reviewer_dashboard, name="reviewer_dashboard"),
    path("layout-dashboard/", layout_dashboard, name="layout_dashboard"),

    path("my-reviews/", my_reviews, name="my_reviews"),
    path("my-submissions/", my_submissions, name="my_submissions"),

    path("submission/<int:submission_id>/review/", review_submission, name="review_submission"),
    path("submission/<int:submission_id>/download-review-paper/", download_review_paper, name="download_review_paper"),
    path("submission/<int:submission_id>/result/", submission_result, name="submission_result"),
    path("submission/<int:submission_id>/decision/", make_decision, name="make_decision"),
    path("submission/<int:submission_id>/delete/", delete_submission, name="delete_submission"),
    path("submission/<int:submission_id>/upload-revision/", upload_revision, name="upload_revision"),
    path("submission/<int:submission_id>/send-revision-to-reviewers/", send_revision_to_reviewers, name="send_revision_to_reviewers"),
    path("submission/<int:submission_id>/layout-decision/", layout_decision, name="layout_decision"),

    path("conference/<slug:slug>/overview/", conference_overview, name="conference_overview"),
    path("conference/<slug:slug>/edit-overview/", edit_conference_overview, name="edit_conference_overview"),
    path("conference/<slug:slug>/settings/", conference_settings, name="conference_settings"),
    path("conference/<slug:slug>/settings/footer/", footer_settings, name="footer_settings"),
    path("conference/<slug:slug>/settings/footer/partner/add/", add_footer_partner, name="add_footer_partner"),
    path("conference/footer/partner/<int:partner_id>/edit/", edit_footer_partner, name="edit_footer_partner"),
    path("conference/footer/partner/<int:partner_id>/delete/", delete_footer_partner, name="delete_footer_partner"),
    path("conference/<slug:slug>/settings/submission/", edit_submission_settings, name="edit_submission_settings"),
    path("conference/<slug:slug>/settings/emails/", email_templates, name="email_templates"),
    path("conference/email-template/<int:template_id>/edit/", edit_email_template, name="edit_email_template"),
    path("conference/email-template/<int:template_id>/preview/", preview_email_template, name="preview_email_template"),

    path("conference/<slug:slug>/important-information/", important_information, name="important_information"),
    path("conference/<slug:slug>/important-information/add/", add_info_card, name="add_info_card"),
    path("important-information/<int:card_id>/edit/", edit_info_card, name="edit_info_card"),
    path("important-information/<int:card_id>/delete/", delete_info_card, name="delete_info_card"),
    path("conference/<slug:slug>/important-information/sidebar/add/", add_sidebar_card, name="add_sidebar_card"),
    path("important-information/sidebar/<int:sidebar_card_id>/edit/", edit_sidebar_card, name="edit_sidebar_card"),
    path("important-information/sidebar/<int:sidebar_card_id>/delete/", delete_sidebar_card, name="delete_sidebar_card"),

    path("conference/<slug:slug>/topics/", conference_topics, name="conference_topics"),
    path("conference/<slug:slug>/topics/add/", add_conference_topic, name="add_conference_topic"),
    path("topics/<int:topic_id>/edit/", edit_conference_topic, name="edit_conference_topic"),
    path("topics/<int:topic_id>/delete/", delete_conference_topic, name="delete_conference_topic"),

    path("conference/<slug:slug>/submit/", submit_paper, name="submit_paper"),
    path("conference/<slug:slug>/assign/", assign_papers, name="assign_papers"),
    path("conference/<slug:slug>/submissions/", conference_submissions, name="conference_submissions"),
    path("conference/<slug:slug>/people/", conference_people, name="conference_people"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)