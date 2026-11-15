import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import storyflow as s


class StoryflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / 'talk'
        s.init_project(self.project,'Test talk',10)
        self.fix_example()

    def tearDown(self):
        self.tmp.cleanup()

    def fix_example(self):
        brief, story, evidence = s.story_items(self.project)
        brief['audience']='Mobile engineers'
        brief['audience_takeaway']='Decide when to change the Core'
        story['big_idea']='Measure end-to-end cost before choosing a language'
        story['opening_question']='Why investigate the Core?'
        story['final_answer']='Optimize the current approach first'
        b1,b2=story['beats']
        b1['question']='Why investigate the Core?'
        b1['next_question']='What should we choose?'
        b1['evidence']=['E1']
        b2['question']='What should we choose?'
        b2['evidence']=['E1']
        evidence['items']=[{'id':'E1','status':'limited','summary':'synthetic test','source':'fixture','scope':'one condition'}]
        s.save(self.project/'brief.json',brief)
        s.save(self.project/'story.json',story)
        s.save(self.project/'evidence.json',evidence)

    def review(self, findings=None, independent=True):
        s.save(self.project/'reviews'/'ai-story-review.json',{
            'fingerprint':s.fingerprint(self.project),
            'reviewer_independent':independent,
            'findings':findings if findings is not None else [],
        })

    def test_initial_status_unverified(self):
        report=s.audit(self.project)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertEqual(report['semantic_review'],'missing')

    def test_board_contains_story_and_feedback(self):
        output,_=s.write_storyboard(self.project)
        doc=output.read_text()
        self.assertIn('Export feedback',doc)
        self.assertIn('Measure end-to-end cost',doc)

    def test_approval_requires_confirmation(self):
        self.review()
        with self.assertRaisesRegex(ValueError,'Human confirmation'):
            s.approve(self.project,'ok',False)

    def test_approval_requires_independent_review_or_explicit_override(self):
        self.review(independent=False)
        with self.assertRaisesRegex(ValueError,'Independent AI'):
            s.approve(self.project,'ok',True)
        s.approve(self.project,'ok',True,'I knowingly waive independent review')

    def test_approval_blocks_major_issue(self):
        self.review([{'beat_id':'B1','severity':'major','status':'open','reason':'Problem is imaginary','fix':'Show baseline'}])
        with self.assertRaisesRegex(ValueError,'critical/major'):
            s.approve(self.project,'ok',True)

    def test_fingerprint_invalidates_approval(self):
        self.review()
        s.approve(self.project,'story approved',True)
        self.assertEqual(s.audit(self.project)['approval'],'current')
        story=s.load(self.project/'story.json')
        story['big_idea']='Something different'
        s.save(self.project/'story.json',story)
        self.assertEqual(s.audit(self.project)['approval'],'STALE')
        with self.assertRaises(ValueError):
            s.draft(self.project)

    def test_draft_requires_approval(self):
        self.review()
        with self.assertRaises(ValueError):s.draft(self.project)
        s.approve(self.project,'ok',True)
        path=s.draft(self.project)
        self.assertTrue(path.exists())
        self.assertIn('story-beat:B1',path.read_text())
        self.assertEqual(s.deck_audit(self.project)['status'],'PASS')

    def test_deck_audit_detects_moved_beat(self):
        self.review()
        s.approve(self.project,'ok',True)
        deck=s.draft(self.project)
        doc=deck.read_text().replace('story-beat:B1','story-beat:TEMP').replace('story-beat:B2','story-beat:B1').replace('story-beat:TEMP','story-beat:B2')
        deck.write_text(doc)
        self.assertEqual(s.deck_audit(self.project)['status'],'FAIL')

    def test_review_fingerprint_stale(self):
        self.review()
        story=s.load(self.project/'story.json')
        story['final_answer']='modified'
        s.save(self.project/'story.json',story)
        self.assertEqual(s.audit(self.project)['semantic_review'],'STALE')

    def test_unknown_evidence_rejected(self):
        story=s.load(self.project/'story.json')
        story['beats'][0]['evidence']=['missing']
        s.save(self.project/'story.json',story)
        self.assertEqual(s.audit(self.project)['status'],'FAIL')

    def test_discontinuity_warned(self):
        story=s.load(self.project/'story.json')
        story['beats'][1]['question']='an unrelated question'
        s.save(self.project/'story.json',story)
        self.assertIn('flow B1 -> B2',' '.join(s.audit(self.project)['warnings']))

    def test_feedback_fingerprint_required(self):
        f=Path(self.tmp.name)/'feedback.json'
        s.save(f,{'fingerprint':'wrong','comments':[{'beat_id':'B1','comment':'fix'}]})
        with self.assertRaisesRegex(ValueError,'different story version'):
            s.import_feedback(self.project,f)
        doc=s.load(f)
        doc['fingerprint']=s.fingerprint(self.project)
        s.save(f,doc)
        s.import_feedback(self.project,f)
        self.assertIn('unincorporated human feedback',' '.join(s.audit(self.project)['warnings']))

    def test_empty_project_protected(self):
        with self.assertRaisesRegex(ValueError,'non-empty'):
            s.init_project(self.project,'Dup',10)

    def test_program_does_not_auto_approve(self):
        s.write_storyboard(self.project)
        self.assertFalse((self.project/'approvals'/'story-approved.json').exists())


if __name__=='__main__':
    unittest.main()
