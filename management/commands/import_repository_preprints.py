from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from repository import models as repo_models
from review import models as review_models
from review.const import ReviewerDecisions as RD, VisibilityOptions as VO
from submission import models as submission_models
from journal import models as journal_models
from utils import setting_handler


RECOMMENDATION_DECISIONS = {
    'accept': RD.DECISION_ACCEPT.value,
    'reject': RD.DECISION_REJECT.value,
    'revise': RD.DECISION_MAJOR.value,
}


class Command(BaseCommand):
    """
    Moves a repository's preprints into the isolinear journal workflow.

    Creates journal articles for published preprints that don't have one and
    copies every invited comment into a journal ReviewAssignment. Runs as a
    dry run unless --commit is passed.
    """

    help = (
        "Creates journal articles for a repository's preprints and copies "
        "their invited comments into journal review assignments."
    )

    def add_arguments(self, parser):
        parser.add_argument('journal_code')
        parser.add_argument('repository_short_name')
        parser.add_argument(
            '--section-id',
            type=int,
            required=True,
            help='Journal section for new articles.',
        )
        parser.add_argument(
            '--license-id',
            type=int,
            help='Journal licence for preprints whose licence has no match.',
        )
        parser.add_argument(
            '--preprint',
            type=int,
            nargs='+',
            dest='preprint_ids',
            help='Only process these preprint IDs.',
        )
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Save the changes. Without this nothing is written.',
        )

    def handle(self, *args, **options):
        try:
            journal = journal_models.Journal.objects.get(
                code=options['journal_code'],
            )
            repository = repo_models.Repository.objects.get(
                short_name=options['repository_short_name'],
            )
            section = submission_models.Section.objects.get(
                pk=options['section_id'],
                journal=journal,
            )
        except (
            journal_models.Journal.DoesNotExist,
            repo_models.Repository.DoesNotExist,
            submission_models.Section.DoesNotExist,
        ) as e:
            raise CommandError(e)

        fallback_licence = None
        if options['license_id']:
            fallback_licence = submission_models.Licence.objects.filter(
                pk=options['license_id'],
                journal=journal,
            ).first()
            if not fallback_licence:
                raise CommandError('No licence with that ID in this journal.')

        form, element = self.get_review_form(journal)
        self.date_due = self.get_date_due(journal)

        preprints = repo_models.Preprint.objects.filter(
            repository=repository,
        ).order_by('pk')
        if options['preprint_ids']:
            preprints = preprints.filter(pk__in=options['preprint_ids'])

        # A dry run must not reach create_article, which copies files to disk.
        self.commit = options['commit']
        with transaction.atomic():
            for preprint in preprints:
                self.process_preprint(
                    preprint,
                    journal,
                    section,
                    fallback_licence,
                    form,
                    element,
                )

        if self.commit:
            self.stdout.write(self.style.SUCCESS('Changes saved.'))
        else:
            self.stdout.write(
                self.style.WARNING('Dry run: nothing saved. Use --commit.'),
            )

    def get_review_form(self, journal):
        form_id = setting_handler.get_setting(
            'general',
            'default_review_form',
            journal,
        ).processed_value
        form = review_models.ReviewForm.objects.filter(
            pk=form_id,
            journal=journal,
        ).first()
        if not form:
            raise CommandError('This journal has no default review form.')
        element = form.elements.filter(kind='textarea').order_by('order').first()
        if not element:
            raise CommandError('The default review form has no text area.')
        return form, element

    def get_date_due(self, journal):
        days = setting_handler.get_setting(
            'general',
            'default_review_days',
            journal,
        ).value
        if not days:
            raise CommandError('This journal has no default review days.')
        return (timezone.now() + timedelta(days=int(days))).date()

    def process_preprint(
        self, preprint, journal, section, fallback_licence, form, element,
    ):
        label = '[{}] {}'.format(preprint.pk, preprint.title[:60])
        article = preprint.article

        if article and article.journal != journal:
            self.stdout.write(
                '{}: linked to article {} in another journal, '
                'skipping.'.format(label, article.pk)
            )
            return

        if not article:
            if preprint.stage != repo_models.STAGE_PREPRINT_PUBLISHED:
                self.stdout.write(
                    '{}: not published ({}), skipping.'.format(
                        label,
                        preprint.stage,
                    )
                )
                return
            licence = self.match_licence(preprint, journal) or fallback_licence
            if not licence:
                self.stdout.write(
                    '{}: no matching journal licence for {}, skipping. '
                    'Pass --license-id.'.format(label, preprint.license)
                )
                return
            stage = self.stage_for(preprint)
            if not self.commit:
                self.stdout.write(
                    '{}: would create an article in stage "{}" '
                    'with licence {}.'.format(label, stage, licence)
                )
                for review in preprint.review_set.all().order_by('pk'):
                    self.stdout.write(
                        '    review {} ({}, {}): would import.'.format(
                            review.pk,
                            review.status,
                            review.reviewer,
                        )
                    )
                return
            article = self.create_article(
                preprint,
                journal,
                section,
                licence,
                stage,
            )
            self.stdout.write(
                '{}: created article {} in stage "{}".'.format(
                    label,
                    article.pk,
                    article.stage,
                )
            )
        else:
            self.stdout.write(
                '{}: already linked to article {}.'.format(label, article.pk)
            )

        for review in preprint.review_set.all().order_by('pk'):
            self.import_review(review, article, form, element)

    def match_licence(self, preprint, journal):
        if not preprint.license:
            return None
        licences = submission_models.Licence.objects.filter(journal=journal)
        url = preprint.license.url.rstrip('/')
        for licence in licences:
            if licence.url.rstrip('/') == url:
                return licence
        return licences.filter(
            short_name=preprint.license.short_name,
        ).first()

    def stage_for(self, preprint):
        if preprint.review_set.exists():
            return submission_models.STAGE_UNDER_REVIEW
        return submission_models.STAGE_UNASSIGNED

    def create_article(self, preprint, journal, section, licence, stage):
        article = preprint.create_article(
            journal=journal,
            workflow_stage=stage,
            journal_license=licence,
            journal_section=section,
        )
        article.date_submitted = preprint.date_submitted or preprint.date_published
        article.correspondence_author = preprint.owner
        article.save()

        for keyword in preprint.keywords.all():
            article.keywords.add(keyword)

        return article

    def import_review(self, review, article, form, element):
        access_code = str(review.access_code)
        if review_models.ReviewAssignment.objects.filter(
            article=article,
            access_code=access_code,
        ).exists():
            self.stdout.write(
                '    review {}: already imported.'.format(review.pk)
            )
            return

        if not self.commit:
            self.stdout.write(
                '    review {} ({}, {}): would import{}.'.format(
                    review.pk,
                    review.status,
                    review.reviewer,
                    ', decision {}'.format(self.decision_for(review))
                    if review.status == 'complete' else '',
                )
            )
            return

        review_round, _ = review_models.ReviewRound.objects.get_or_create(
            article=article,
            round_number=1,
        )
        assignment = review_models.ReviewAssignment(
            article=article,
            reviewer=review.reviewer,
            editor=review.manager,
            review_round=review_round,
            form=form,
            access_code=access_code,
            date_due=self.date_due,
            visibility=VO.SINGLE_ANON.value if review.anonymous else VO.OPEN.value,
            comments_for_editor=review.status_reason,
        )

        if review.status == 'accepted':
            assignment.date_accepted = review.date_accepted
        elif review.status == 'declined':
            assignment.date_declined = review.date_completed
            assignment.is_complete = True
        elif review.status == 'withdrawn':
            assignment.decision = RD.DECISION_WITHDRAWN.value
            assignment.date_complete = review.date_completed
            assignment.is_complete = True
        elif review.status == 'complete':
            assignment.date_accepted = review.date_accepted
            assignment.date_complete = review.date_completed
            assignment.is_complete = True
            assignment.decision = self.decision_for(review)

        if review.comment and review.comment.is_public:
            assignment.permission_to_make_public = True
            assignment.display_public = True

        assignment.save()

        if review.date_assigned:
            review_models.ReviewAssignment.objects.filter(
                pk=assignment.pk,
            ).update(date_requested=review.date_assigned)

        if review.comment:
            answer = review_models.ReviewAssignmentAnswer.objects.create(
                assignment=assignment,
                original_element=element,
                answer=review.comment.body,
                author_can_see=element.default_visibility,
            )
            element.snapshot(answer)

        self.stdout.write(
            '    review {} ({}, {}): imported as assignment {}{}.'.format(
                review.pk,
                review.status,
                review.reviewer,
                assignment.pk,
                ', decision {}'.format(assignment.decision)
                if assignment.decision else '',
            )
        )

    def decision_for(self, review):
        if not review.recommendation:
            return RD.DECISION_NO_RECOMMENDATION.value
        return RECOMMENDATION_DECISIONS.get(
            review.recommendation.name.strip().lower(),
            RD.DECISION_NO_RECOMMENDATION.value,
        )
