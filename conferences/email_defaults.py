OFFICIAL_EMAIL_EVENTS = [
    "committee_login_info",
    "paper_submitted",
    "coauthor_submission_confirmation",
    "review_invitation",
    "review_request_accepted",
    "review_initiated",
    "review_due_soon",
    "review_overdue",
    "review_received",
    "rereview_invitation",
    "reviewer_editor_decision",
    "review_completed_author",
    "manuscript_accepted",
    "layout_correction_needed",
    "layout_correction_submitted",
]

DEFAULT_EMAIL_TEMPLATES_2026 = {
    "committee_login_info": {
        "enabled": False,
        "subject": "Information for Scientific Committee members – {{ conference_name }}",
        "body": """Dear Scientific Committee Member/Reviewer,\n\nIt is my great pleasure to inform you that we have created a hub for all conference communication at the following link:\n{{ conference_link }}\n\nYour login details are:\nUsername: {{ reviewer_email }}\nPassword: {{ temporary_password }}\n\nFor more details, please visit the official conference website.\n\nWe are honoured to have you as part of the Conference Scientific Committee, and look forward to our future cooperation.\n\nKind regards,\n\nProf. Dr. Ljiljana Vasilevska\nConference Scientific Committee Chair\nFaculty of Civil Engineering and Architecture\nUniversity of Niš\nNiš, Serbia""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "paper_submitted": {
        "subject": "Submission Confirmation – Manuscript: {{ paper_title }}",
        "body": """Dear Author,\n\nThank you for submitting your paper titled {{ paper_title }} (Identifier: {{ paper_code }}). We acknowledge receipt of your submission and appreciate your trust in our Conference.\n\nPlease take note of the paper number provided above and use it in all future correspondence related to this submission. This will help us efficiently track and address any queries or updates regarding your manuscript.\n\nOur team of editors and reviewers will thoroughly assess the content of your manuscript and provide their expert insights. We will keep you informed as soon as a decision has been reached by the editorial board.\n\nIf you have any questions or require further assistance, please contact our Editorial Office ({{ conference_contact_email }}).\n\nKind Regards,\nThe Editorial Office\nGreen Building International Scientific Conference""",
        "send_to_author": True, "send_to_coauthors": False,
    },
    "coauthor_submission_confirmation": {
        "subject": "Co-author Submission Confirmation – Manuscript: {{ paper_title }}",
        "body": """Dear Co-Author,\n\nThis is an automatic notification to inform you that the manuscript entitled {{ paper_title }} (Identifier: {{ paper_code }}) has been submitted online by {{ submitting_author_name }}.\n\nTo ensure accurate representation and proper authorization, we kindly inform you that you are listed as a co-author.\n\nIf you are not a co-author or believe there has been an error, please contact the editorial office immediately via {{ conference_contact_email }}.\n\nThroughout the publication process, all correspondence regarding this manuscript will be sent to the submitting author as designated by the editorial office.\n\nKind Regards,\nThe Editorial Board\nGreen Building International Scientific Conference\n\nMANUSCRIPT DETAILS\nManuscript title: {{ paper_title }}\nManuscript ID: {{ paper_code }}\nArticle type: {{ article_type }}\nSubmitted on: {{ submitted_on }}\nAbstract:\n{{ abstract }}""",
        "send_to_author": False, "send_to_coauthors": True,
    },
    "review_invitation": {
        "subject": "Invitation to Review Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nWe are writing to extend an invitation to you as a potential reviewer of the manuscript entitled {{ paper_title }}, which has been submitted to Green Building Conference.\n\nWe kindly invite you to review this paper and evaluate its suitability for publication in the Green Building International Scientific Conference Proceedings. The article abstract is available at the end of this message.\n\nIf you choose to accept this invitation, we kindly request that you provide your comments within {{ review_days }} days. However, if you require additional time, you may request an extension for submitting your review.\n\nTo respond to this review invitation and access the full manuscript and review report form, please click on the link below:\n{{ review_link }}\n\nThank you for considering our invitation. Your expertise and contributions are highly valued.\n\nKind Regards,\nThe Editorial Board\nGreen Building International Scientific Conference\n\nMANUSCRIPT DETAILS\nManuscript title: {{ paper_title }}\nManuscript ID: {{ paper_code }}\nArticle type: {{ article_type }}\nSubmitted on: {{ submitted_on }}\nAbstract:\n{{ abstract }}\nKeywords: {{ keywords }}\n\nNote: Reviewers are obliged to keep all manuscript files confidential. For technical issues, please contact us at {{ conference_contact_email }}.""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "review_request_accepted": {
        "subject": "Review Request Accepted – Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nThank you for accepting the invitation to review the following manuscript:\n\nManuscript ID: {{ paper_code }}\nManuscript Type: {{ article_type }}\nTitle: {{ paper_title }}\n\nTo provide your review, please use the review report form available at the following link:\n{{ review_link }}\n\nThe deadline for submitting your review report is {{ review_deadline }}.\n\nReviews should provide detailed, constructive, and well-argued comments that help the authors improve the quality and clarity of their manuscript. Comments should be formulated in a professional, respectful, and collegial manner.\n\nKind Regards,\nThe Editorial Office\nGreen Building International Scientific Conference""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "review_initiated": {
        "subject": "Review Initiated – Manuscript: {{ paper_title }}",
        "body": """Dear Author,\n\nThank you very much for providing your paper:\n\nManuscript: {{ paper_code }}\nType of Manuscript: {{ article_type }}\nTitle: {{ paper_title }}\nAuthors: {{ all_authors }}\nDate Received: {{ submitted_on }}\nE-mails: {{ all_author_emails }}\n\nWe would like to inform you that your paper is now being reviewed.\n\nKind Regards,\nThe Editorial Team\nGreen Building International Scientific Conference""",
        "send_to_author": True, "send_to_coauthors": True,
    },
    "review_due_soon": {
        "subject": "Reminder: Agreed review due soon – Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nWe are writing to kindly remind you that the review you have agreed to undertake for our conference is due in {{ days_until_due }} days.\n\nManuscript title: {{ paper_title }}\nManuscript ID: {{ paper_code }}\nDate agreed: {{ date_agreed }}\n\nTo provide your review, please use the review report form available at the following link:\n{{ review_link }}\n\nIf you require additional time to finalize your evaluation, please inform us as soon as possible.\n\nYours sincerely,\nThe Editorial Office\nGreen Building International Scientific Conference""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "review_overdue": {
        "subject": "Reminder: Review overdue – Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nThank you for agreeing to review the following manuscript for us.\n\nManuscript title: {{ paper_title }}\nManuscript ID: {{ paper_code }}\n\nThis is a reminder that your review was due on {{ review_deadline }}.\n\nTo access the manuscript, please click on the following link:\n{{ review_link }}\n\nIf you anticipate a delay in submitting your review, please contact the editorial office by replying to this email.\n\nBest regards,\nEditorial Office\nGreen Building International Scientific Conference\n\nIf you submitted your review earlier today, thank you. Please disregard this automatically-generated notification.""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "review_received": {
        "subject": "Confirmation of Review Receipt – Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nThank you for taking the time to review the manuscript titled {{ paper_title }} (Identifier: {{ paper_code }}) for International Scientific Conference Green Building. We greatly appreciate your valuable contribution to the peer-review process.\n\nThis email serves as confirmation that we have successfully received your review.\n\nThank you once again for your valuable review and for supporting International Scientific Conference Green Building.\n\nKind Regards,\nThe Editorial Office\nGreen Building International Scientific Conference""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "rereview_invitation": {
        "subject": "Invitation to Re-evaluate Revised Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nI am writing to invite you to re-evaluate the revised manuscript titled {{ paper_title }} (Identifier: {{ paper_code }}), which has been resubmitted to International Scientific Conference Green Building.\n\nWe have allocated {{ review_days }} days for the re-evaluation phase. To indicate your willingness to re-evaluate the manuscript, please click on the link provided below:\n{{ review_link }}\n\nEditor's comment:\n{{ editor_comments }}\n\nKind Regards,\nThe Editorial Team\nGreen Building International Scientific Conference\nFor technical issues, please contact us at {{ conference_contact_email }}\n\nMANUSCRIPT DETAILS\nManuscript title: {{ paper_title }}\nManuscript ID: {{ paper_code }}\nArticle type: {{ article_type }}\nSubmitted on: {{ submitted_on }}\nAbstract:\n{{ abstract }}""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "reviewer_editor_decision": {
        "subject": "Reviewer Notification of Editor Decision – Manuscript: {{ paper_title }}",
        "body": """Dear Reviewer,\n\nThank you once again for reviewing the manuscript {{ paper_title }}. With your help the following final decision has now been reached:\n\n{{ editor_decision }}\n\nThe editor's decision letter and reviewer comments can be found below.\n\nWe appreciate your time and effort in reviewing this paper and greatly value your assistance as a reviewer for Green Building International Scientific Conference.\n\nYours sincerely,\nEditorial Team\nGreen Building International Scientific Conference\n\nEditor Comments to Author\n{{ editor_comments }}\n\nReviewer(s)' Comments to Author:\n{{ reviewer_comments }}""",
        "send_to_author": False, "send_to_coauthors": False, "send_to_reviewer": True,
    },
    "review_completed_author": {
        "subject": "Review Completed – Manuscript: {{ paper_title }}",
        "body": """Dear Author,\n\nThank you once again for submitting your manuscript. The following decision has now been reached:\n\n{{ editor_decision }}\n\nThe editor's decision letter and reviewer comments can be found below.\n\nPlease revise your manuscript according to provided comments by: {{ revision_deadline }}\n\nEditor Comments to Author\n{{ editor_comments }}\n\nReviewer(s)' Comments to Author:\n{{ reviewer_comments }}\n\nKind Regards,\nThe Editorial Board\nGreen Building International Scientific Conference""",
        "send_to_author": True, "send_to_coauthors": True,
    },
    "manuscript_accepted": {
        "subject": "Manuscript accepted for publication: {{ paper_title }}",
        "body": """Dear Author,\n\nIt is a pleasure to accept your manuscript entitled {{ paper_title }} in its current form for publication in the Green Building Conference Proceedings. Congratulations!\n\nBelow are comments from the editor and reviewers.\n\nYour accepted manuscript will now be transferred to layout reviewer and work will begin on creation of the proof. If we need any additional information to create the proof, we will let you know.\n\nKind Regards,\nThe Editorial Team\n\nEditor Comments to Author\n{{ editor_comments }}\n\nReviewer(s)' Comments to Author:\n{{ reviewer_comments }}""",
        "send_to_author": True, "send_to_coauthors": True,
    },
    "layout_correction_needed": {
        "subject": "Layout correction needed – Paper: {{ paper_title }}",
        "body": """Dear Author,\n\nWe invite you to complete the Layout correction needed before {{ layout_deadline }} to ensure that we can proceed with the publication of your paper. If you need more time, please inform the Editor of the expected date that will suit you.\n\nPlease correct your manuscript following the instructions in the comments written in the file.\n\nPlease see further details here:\n{{ upload_revision_link }}\n\nWe look forward to hearing from you soon.\n\nKind regards,\nThe Publishing Team\nGreen Building International Scientific Conference""",
        "send_to_author": True, "send_to_coauthors": True,
    },
    "layout_correction_submitted": {
        "subject": "Author's correction submitted – Paper: {{ paper_title }}",
        "body": """Dear Author,\n\nThe Layout correction of your manuscript, {{ paper_title }}, has been successfully submitted.\n\nThank you for your contribution.\n\nKind regards,\nThe Editorial Team\nGreen Building International Scientific Conference""",
        "send_to_author": True, "send_to_coauthors": True,
    },
}
