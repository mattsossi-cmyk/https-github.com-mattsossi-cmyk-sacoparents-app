"""Shared Professional Legal Report constants (used by legal_report and sample_professional_report)."""
PURPOSE = ("This Professional Legal Report organizes information provided through SA CoParents assessments and related case materials for review by the "
           "authorized professional. Parent-reported information should not be interpreted as independently verified fact unless specifically identified as such by the professional.")
SAFETY_NOTICE = ("Communication, mediation, joint decision-making, and other dispute-resolution options should be considered in light of any disclosed safety concerns, "
                 "allegations of family violence, protective orders, coercive control concerns, or other circumstances affecting safety and informed participation.")
CERTIFICATION = ("I have reviewed this report and understand that AI-generated or system-generated language is a drafting aid. I am responsible for the professional "
                 "observations, conclusions, selections, and statements contained in the finalized report.")
OPTIONS_LIBRARY = ["SA CoParents Communication Builder", "BIFF communication principles", "Structured written communication", "OurFamilyWizard", "ToneMeter",
                   "Children in the Middle", "Co-Parenting Education", "Child-Focused Mediation", "Traditional Mediation", "Parent Facilitation", "Parent Coordination",
                   "Therapeutic Support", "Educational Professional Consultation", "Medical Professional Consultation", "Mental Health Professional Consultation",
                   "Collaborative Law", "Attorney-to-Attorney Negotiation", "Court Resolution"]
PATHS = ["Continue Direct Co-Parenting Work", "Structured Communication", "Child-Focused Mediation", "Traditional Mediation", "Parent Facilitation / Coordination",
         "Collaborative Process", "Professional Consultation", "Legal Negotiation", "Court Determination", "Other"]
PARENT_HEADINGS = [("needs_most", "Child-focused priorities"), ("working_well", "Areas the parent believes are working"), ("concerns", "Primary parenting concerns"),
                   ("improve", "Goals for resolution"), ("options", "Options the parent would consider"), ("other_parent", "The parent's view of the other parent's likely concerns")]
CHILD_TOPICS = {"schedule": "Parenting schedule", "holidays": "Parenting schedule", "education": "Education", "medical": "Medical care", "psychological": "Mental/behavioral health",
                "activities": "Extracurricular activities", "transitions": "Transitions", "communication": "Communication concerning the child", "technology": "Communication concerning the child",
                "decision_making": "Decision-making", "special_needs": "Special needs", "child_needs": "Other child-specific concerns", "routine": "Other child-specific concerns"}
EDITABLE = ("observations", "further_attention", "alignment_areas", "partial_alignment", "procedural_considerations", "professional_comments", "options_resources",
            "options_custom", "conflict_resolution_paths", "conflict_resolution_explanation", "include_parent_summaries_in_court", "role")
LENS_MAP = {"professional_observations": "observations", "issues_requiring_attention": "further_attention", "existing_agreements": "alignment_areas",
            "agreement_building_opportunities": "partial_alignment", "procedural_considerations": "procedural_considerations"}
BANNED_LABELS = ("narcissist", "abusive", "alienat", "unstable", "mentally ill", "dangerous", "deceptive")

