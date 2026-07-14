"""Entity-section descriptors for the card-context and module tables, consumed by
the generic :mod:`entities` engine.

Listed in dependency order: a section's intra-module parents come first
(``PpmWbs`` before ``PpmTask`` before ``PpmTaskComment``; ``Risk`` before
``RiskCard``/``RiskMitigationTask`` before the occurrences; ``ArchitectureDecision``
before its card links; ``Survey`` before ``SurveyResponse``). Cards and relations
are applied earlier by the bespoke core sections, so card FKs always resolve.
"""

from __future__ import annotations

from app.models.adm import AdmPhase, AdmPhaseArtefact, AdmWorkspace
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.architecture_decision_card import ArchitectureDecisionCard
from app.models.bookmark import Bookmark
from app.models.comment import Comment
from app.models.diagram import Diagram
from app.models.diagram_favorite import DiagramFavorite
from app.models.diagram_group import DiagramGroup
from app.models.document import Document
from app.models.ea_requirement import EaRequirement, EaRequirementCard
from app.models.file_attachment import FileAttachment
from app.models.improvement_opportunity import (
    ImprovementOpportunity,
    ImprovementOpportunityCard,
)
from app.models.maturity import (
    MaturityAssessment,
    MaturityDimension,
    MaturityDimensionScore,
)
from app.models.nora_landscape import NoraPlateau, NoraSegment
from app.models.nora_program import EaProgramDeliverable
from app.models.ppm_cost_line import PpmBudgetLine, PpmCostLine
from app.models.ppm_dependency import PpmDependency
from app.models.ppm_risk import PpmRisk
from app.models.ppm_status_report import PpmStatusReport
from app.models.ppm_task import PpmTask
from app.models.ppm_task_comment import PpmTaskComment
from app.models.ppm_wbs import PpmWbs
from app.models.process_assessment import ProcessAssessment
from app.models.process_diagram import ProcessDiagram
from app.models.process_element import ProcessElement
from app.models.process_flow_version import ProcessFlowVersion
from app.models.rationalization import AssessmentDecision, RationalizationAssessment
from app.models.reference_model import ReferenceModel, ReferenceModelItem
from app.models.risk import Risk, RiskCard
from app.models.risk_mitigation_task import RiskMitigationTask, RiskMitigationTaskOccurrence
from app.models.roadmap import Roadmap, RoadmapMilestone
from app.models.saved_report import SavedReport
from app.models.scenario import Scenario, ScenarioChange
from app.models.soaw import SoAW
from app.models.stakeholder import Stakeholder
from app.models.survey import Survey, SurveyResponse
from app.models.tech_standard import StandardException, TechStandard
from app.models.todo import Todo
from app.models.web_portal import WebPortal
from app.services.workspace_io.entities import EntitySection

# Sheet name for the bespoke Diagram↔Card association (handled like CardTags).
SHEET_DIAGRAM_CARDS = "DiagramCards"
# Sheet name for the bespoke Diagram↔Group association (both PKs preserved).
SHEET_DIAGRAM_GROUP_MEMBERS = "DiagramGroupMembers"

ENTITY_SECTIONS: tuple[EntitySection, ...] = (
    # --- Card context ----------------------------------------------------
    EntitySection(
        "Stakeholders", Stakeholder, card_fk_columns=("card_id",), user_fk_columns=("user_id",)
    ),
    EntitySection(
        "Documents", Document, card_fk_columns=("card_id",), user_fk_columns=("created_by",)
    ),
    EntitySection(
        "Comments",
        Comment,
        card_fk_columns=("card_id",),
        user_fk_columns=("user_id",),
        self_parent_column="parent_id",
    ),
    EntitySection(
        "Todos",
        Todo,
        card_fk_columns=("card_id",),
        user_fk_columns=("assigned_to", "created_by"),
    ),
    EntitySection(
        "FileAttachments",
        FileAttachment,
        card_fk_columns=("card_id",),
        user_fk_columns=("created_by",),
        asset_columns=(("data", "bytes", "bin"),),
        filename_column="name",  # keep the original filename + extension
    ),
    EntitySection(
        "Diagrams",
        Diagram,
        user_fk_columns=("created_by",),
        # Extract the DrawIO XML from data["xml"] into a real .drawio file;
        # the thumbnail / view / card_refs keys stay inline as JSON.
        json_asset_columns=(("data", "xml", "drawio"),),
        filename_column="name",
    ),
    # Diagram groups (shared) + per-user favorites. After Diagrams so the
    # favorites' diagram_id (an intra-module FK, preserved verbatim) resolves.
    EntitySection("DiagramGroups", DiagramGroup, user_fk_columns=("created_by",)),
    EntitySection("DiagramFavorites", DiagramFavorite, user_fk_columns=("user_id",)),
    # --- BPM --------------------------------------------------------------
    EntitySection(
        "ProcessDiagrams",
        ProcessDiagram,
        card_fk_columns=("process_id",),
        user_fk_columns=("created_by",),
        asset_columns=(("bpmn_xml", "text", "bpmn"), ("svg_thumbnail", "text", "svg")),
    ),
    EntitySection(
        "ProcessElements",
        ProcessElement,
        card_fk_columns=("process_id", "application_id", "data_object_id", "it_component_id"),
    ),
    EntitySection(
        "ProcessFlowVersions",
        ProcessFlowVersion,
        card_fk_columns=("process_id",),
        user_fk_columns=("created_by", "submitted_by", "approved_by"),
        self_parent_column="based_on_id",
        asset_columns=(("bpmn_xml", "text", "bpmn"), ("svg_thumbnail", "text", "svg")),
    ),
    EntitySection(
        "ProcessAssessments",
        ProcessAssessment,
        card_fk_columns=("process_id",),
        user_fk_columns=("assessor_id",),
    ),
    # --- PPM (wbs before task before comment/dependency) -----------------
    EntitySection(
        "PpmStatusReports",
        PpmStatusReport,
        card_fk_columns=("initiative_id",),
        user_fk_columns=("reporter_id",),
    ),
    EntitySection("PpmCostLines", PpmCostLine, card_fk_columns=("initiative_id",)),
    EntitySection("PpmBudgetLines", PpmBudgetLine, card_fk_columns=("initiative_id",)),
    EntitySection(
        "PpmRisks", PpmRisk, card_fk_columns=("initiative_id",), user_fk_columns=("owner_id",)
    ),
    EntitySection(
        "PpmWbs",
        PpmWbs,
        card_fk_columns=("initiative_id",),
        user_fk_columns=("assignee_id",),
        self_parent_column="parent_id",
    ),
    EntitySection(
        "PpmTasks", PpmTask, card_fk_columns=("initiative_id",), user_fk_columns=("assignee_id",)
    ),
    EntitySection("PpmTaskComments", PpmTaskComment, user_fk_columns=("user_id",)),
    EntitySection("PpmDependencies", PpmDependency, card_fk_columns=("initiative_id",)),
    # --- GRC risk register -----------------------------------------------
    EntitySection("Risks", Risk, user_fk_columns=("owner_id", "accepted_by", "created_by")),
    EntitySection("RiskCards", RiskCard, card_fk_columns=("card_id",)),
    EntitySection(
        "RiskMitigationTasks", RiskMitigationTask, user_fk_columns=("owner_id", "created_by")
    ),
    EntitySection(
        "RiskMitTaskOccurrences",
        RiskMitigationTaskOccurrence,
        user_fk_columns=("assigned_owner_id", "completed_by", "owner_at_completion"),
    ),
    # --- Governance / delivery -------------------------------------------
    EntitySection(
        "Adrs",
        ArchitectureDecision,
        user_fk_columns=("created_by",),
        self_parent_column="parent_id",
    ),
    EntitySection("AdrCards", ArchitectureDecisionCard, card_fk_columns=("card_id",)),
    EntitySection(
        "Soaws",
        SoAW,
        card_fk_columns=("initiative_id",),
        user_fk_columns=("created_by",),
        self_parent_column="parent_id",
    ),
    # --- ADM Governance Workspace (workspace → phases → artefacts) ---------
    # SoAW module rows keep their UUIDs on import, so ``soaw_id`` resolves
    # verbatim. ``initiative_id`` points at a card and is remapped via
    # ``card_fk_columns``. Artefact ``ref_id`` is a soft FK dispatched by
    # ``kind`` at the API layer; when the referenced entity is a card the
    # remap needs to happen too, but for the MVP we accept that a workspace
    # transfer will leave ``kind='card'`` refs pointing at the old UUIDs.
    # A follow-up should extend :class:`EntitySection` with a
    # ``polymorphic_ref`` hook to cover this correctly.
    EntitySection(
        "AdmWorkspaces",
        AdmWorkspace,
        card_fk_columns=("initiative_id",),
        user_fk_columns=("owner_id", "created_by"),
    ),
    EntitySection(
        "AdmPhases",
        AdmPhase,
        user_fk_columns=("owner_id", "approved_by"),
    ),
    EntitySection(
        "AdmPhaseArtefacts",
        AdmPhaseArtefact,
        user_fk_columns=("waived_by", "linked_by"),
    ),
    # --- Transformation roadmaps (roadmap before its milestones) ---------
    EntitySection("Roadmaps", Roadmap, user_fk_columns=("owner_id",)),
    EntitySection("RoadmapMilestones", RoadmapMilestone, card_fk_columns=("initiative_id",)),
    # --- Rationalization (assessment before its decisions) -----------------
    EntitySection(
        "RationalizationAssessments",
        RationalizationAssessment,
        user_fk_columns=("created_by",),
    ),
    EntitySection(
        "AssessmentDecisions",
        AssessmentDecision,
        card_fk_columns=("card_id", "successor_id", "initiative_id"),
    ),
    # --- Technology standards (standard before its exceptions) -----------
    # replacement_id is an intra-module self-FK; module rows keep their PKs on
    # import so it resolves verbatim (no remap needed).
    # tech_category_id points at a TechCategory card (NORA TRM link, WP1.3) —
    # card PKs are reassigned on import, so it must go through the card remap.
    EntitySection(
        "TechStandards",
        TechStandard,
        card_fk_columns=("tech_category_id",),
        user_fk_columns=("owner_id",),
    ),
    EntitySection(
        "StandardExceptions",
        StandardException,
        card_fk_columns=("card_id", "initiative_id"),
        user_fk_columns=("approver_id", "created_by"),
    ),
    # --- NORA EA Program tracker (WP3.1) ----------------------------------
    EntitySection(
        "EaProgramDeliverables",
        EaProgramDeliverable,
        user_fk_columns=("owner_id", "approved_by"),
    ),
    # --- EA requirements register (WP6.1, requirement before its links) ---
    EntitySection(
        "EaRequirements",
        EaRequirement,
        card_fk_columns=("initiative_id",),
        user_fk_columns=("created_by", "approved_by"),
    ),
    EntitySection(
        "EaRequirementCards",
        EaRequirementCard,
        card_fk_columns=("card_id",),
    ),
    # --- Improvement opportunities (WP3.3, opportunity before its links) ---
    EntitySection(
        "ImprovementOpportunities",
        ImprovementOpportunity,
        card_fk_columns=("initiative_id", "journey_card_id"),
        user_fk_columns=("created_by",),
    ),
    EntitySection(
        "ImprovementOpportunityCards",
        ImprovementOpportunityCard,
        card_fk_columns=("card_id",),
    ),
    # --- EA maturity self-assessment (WP5.2, dimension → assessment → score) ---
    EntitySection("MaturityDimensions", MaturityDimension),
    EntitySection(
        "MaturityAssessments",
        MaturityAssessment,
        user_fk_columns=("created_by", "approved_by"),
    ),
    EntitySection("MaturityDimensionScores", MaturityDimensionScore),
    # --- NORA plateaus + segment scopes (WP5.4) ---------------------------
    EntitySection("NoraPlateaus", NoraPlateau),
    EntitySection("NoraSegments", NoraSegment, card_fk_columns=("root_card_id",)),
    # --- Reference models (WP100.3, model before its items) ---------------
    EntitySection(
        "ReferenceModels",
        ReferenceModel,
        user_fk_columns=("created_by", "published_by"),
    ),
    EntitySection(
        "ReferenceModelItems",
        ReferenceModelItem,
        self_parent_column="parent_id",
    ),
    # --- Architecture Review Board ---------------------------------------
    EntitySection(
        "ArbReviews",
        ArbReview,
        card_fk_columns=("subject_card_id",),
        user_fk_columns=("reviewer_id", "created_by"),
    ),
    # --- Scenario planning (scenario before its changes) -----------------
    EntitySection("Scenarios", Scenario, user_fk_columns=("created_by", "merged_by")),
    EntitySection("ScenarioChanges", ScenarioChange, card_fk_columns=("target_card_id",)),
    # --- Saved views + surveys -------------------------------------------
    EntitySection("SavedReports", SavedReport, user_fk_columns=("owner_id",)),
    EntitySection("Bookmarks", Bookmark, user_fk_columns=("user_id",)),
    EntitySection("WebPortals", WebPortal, user_fk_columns=("created_by",)),
    EntitySection("Surveys", Survey, user_fk_columns=("created_by",)),
    EntitySection(
        "SurveyResponses",
        SurveyResponse,
        card_fk_columns=("card_id",),
        user_fk_columns=("user_id",),
    ),
)
