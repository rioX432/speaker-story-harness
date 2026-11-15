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
        self.assertIn('修正指示を書き出す',doc)
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


    def write_candidates(self, recommended='C1'):
        def cand(cid):
            return {'id':cid,'title':f'title {cid}','audience_problem':'p','big_idea':'b','logic':['l1','l2'],
                    'key_findings':['k'],'takeaway_criteria':['t'],'failure_risks':['r']}
        s.save(self.project/'candidates.json',{'recommended':recommended,'recommendation_reason':'because',
                                               'candidates':[cand('C1'),cand('C2')]})

    def strip_new_fields(self):
        brief, story, evidence = s.story_items(self.project)
        brief.pop('review_checks',None)
        for b in story['beats']:
            b.pop('from_previous',None)
            b.pop('risks',None)
        s.save(self.project/'brief.json',brief)
        s.save(self.project/'story.json',story)
        (self.project/'candidates.json').unlink()

    def test_old_format_story_still_works_and_shows_unfilled(self):
        self.strip_new_fields()
        report=s.audit(self.project)
        self.assertEqual(report['errors'],[])
        self.assertEqual(report['candidate_review'],'none')
        doc=s.write_storyboard(self.project)[0].read_text()
        self.assertIn('前章からのつながり',doc)
        self.assertIn('未記入',doc)
        self.assertIn('既定の観点',doc)
        self.review()
        s.approve(self.project,'ok',True)
        self.assertTrue(s.draft(self.project).exists())

    def test_fingerprint_ignores_candidates_and_absent_new_fields_change_nothing(self):
        before=s.fingerprint(self.project)
        self.write_candidates()
        self.assertEqual(s.fingerprint(self.project),before)
        cfp=s.candidates_fingerprint(self.project)
        self.write_candidates(recommended='C2')
        self.assertNotEqual(s.candidates_fingerprint(self.project),cfp)
        (self.project/'candidates.json').unlink()
        self.assertIsNone(s.candidates_fingerprint(self.project))

    def test_board_shows_new_beat_fields_and_evidence_details(self):
        story=s.load(self.project/'story.json')
        story['beats'][1]['from_previous']='Because B1 showed the cost'
        story['beats'][1]['risks']=[{'risk':'Only one device','fix':'Say the scope at the start'}]
        s.save(self.project/'story.json',story)
        ev=s.load(self.project/'evidence.json')
        ev['items'][0]['kind']='experiment'
        ev['items'][0]['url']='https://example.com/log'
        s.save(self.project/'evidence.json',ev)
        doc=s.write_storyboard(self.project)[0].read_text()
        for text in ('Because B1 showed the cost','Only one device','Say the scope at the start',
                     'synthetic test','one condition','fixture','実験・PoC','条件付き','https://example.com/log'):
            self.assertIn(text,doc)
        for n in range(1,9):
            self.assertIn(f"<span class='n'>{n}</span>",doc)

    def test_invalid_risk_and_kind_rejected(self):
        story=s.load(self.project/'story.json')
        story['beats'][0]['risks']=[{'risk':'vague'}]
        s.save(self.project/'story.json',story)
        self.assertIn('each risk needs risk and a concrete fix',' '.join(s.audit(self.project)['errors']))
        story['beats'][0]['risks']=[]
        s.save(self.project/'story.json',story)
        ev=s.load(self.project/'evidence.json')
        ev['items'][0]['kind']='rumor'
        s.save(self.project/'evidence.json',ev)
        self.assertIn('kind must be',' '.join(s.audit(self.project)['errors']))

    def test_candidate_structure_errors_and_warnings(self):
        self.write_candidates(recommended='C9')
        self.assertIn("recommended 'C9'",' '.join(s.audit(self.project)['errors']))
        doc=s.load(self.project/'candidates.json')
        doc['recommended']='C1'
        doc['candidates'][1]['id']='C1'
        s.save(self.project/'candidates.json',doc)
        self.assertIn('duplicate candidate id',' '.join(s.audit(self.project)['errors']))
        self.write_candidates()
        story=s.load(self.project/'story.json')
        story['candidate_id']='C7'
        s.save(self.project/'story.json',story)
        self.assertIn("candidate_id 'C7'",' '.join(s.audit(self.project)['errors']))
        story['candidate_id']='C1'
        s.save(self.project/'story.json',story)
        report=s.audit(self.project)
        self.assertEqual(report['errors'],[])
        self.assertEqual(report['candidate_review'],'missing')

    def test_candidate_review_current_then_stale(self):
        self.write_candidates()
        s.save(self.project/'reviews'/'ai-candidate-review.json',{
            'fingerprint':s.candidates_fingerprint(self.project),'reviewer_independent':True,'summary':'ok',
            'candidates':[{'candidate_id':'C1','verdict':'strong','strengths':['clear'],'breakpoints':['thin data']}]})
        self.assertEqual(s.audit(self.project)['candidate_review'],'current')
        doc=s.write_storyboard(self.project)[0].read_text()
        self.assertIn('thin data',doc)
        self.assertIn('推奨',doc)
        self.write_candidates(recommended='C2')
        self.assertEqual(s.audit(self.project)['candidate_review'],'STALE')

    def test_default_and_custom_review_checks(self):
        self.strip_new_fields()
        self.assertEqual(s.review_checks(s.load(self.project/'brief.json')),(list(s.DEFAULT_REVIEW_CHECKS),False))
        brief=s.load(self.project/'brief.json')
        brief['review_checks']=['Is the baseline fair?']
        s.save(self.project/'brief.json',brief)
        self.review()
        req=s.review_request(self.project).read_text()
        self.assertIn('Is the baseline fair?',req)
        doc=s.write_storyboard(self.project)[0].read_text()
        self.assertIn('Is the baseline fair?',doc)
        self.assertNotIn(s.DEFAULT_REVIEW_CHECKS[0],doc)
        brief['review_checks']=['']
        s.save(self.project/'brief.json',brief)
        self.assertIn('review_checks',' '.join(s.audit(self.project)['errors']))

    def test_review_check_verdicts(self):
        check=s.DEFAULT_REVIEW_CHECKS[0]
        s.save(self.project/'reviews'/'ai-story-review.json',{'fingerprint':s.fingerprint(self.project),
            'reviewer_independent':True,'findings':[],'checks':[{'check':check,'verdict':'maybe','reason':'x'}]})
        self.assertIn('verdict pass/partial/fail/unknown',' '.join(s.audit(self.project)['errors']))
        s.save(self.project/'reviews'/'ai-story-review.json',{'fingerprint':s.fingerprint(self.project),
            'reviewer_independent':True,'findings':[],'checks':[{'check':check,'verdict':'fail','reason':'no need shown'}]})
        self.assertIn('needs a concrete fix',' '.join(s.audit(self.project)['errors']))
        s.save(self.project/'reviews'/'ai-story-review.json',{'fingerprint':s.fingerprint(self.project),
            'reviewer_independent':True,'findings':[],'checks':[{'check':check,'verdict':'fail','reason':'no need shown','fix':'add a baseline chapter'}]})
        report=s.audit(self.project)
        self.assertEqual(report['errors'],[])
        self.assertIn('story check not met (fail)',' '.join(report['warnings']))
        doc=s.write_storyboard(self.project)[0].read_text()
        self.assertIn('add a baseline chapter',doc)

    def test_feedback_candidate_choice_validated(self):
        self.write_candidates()
        f=Path(self.tmp.name)/'feedback.json'
        base={'fingerprint':s.fingerprint(self.project),'comments':[],'candidate_choice':{'selected':'C2','instruction':'use C2'}}
        s.save(f,dict(base,candidates_fingerprint='old'))
        with self.assertRaisesRegex(ValueError,'different candidates.json version'):
            s.import_feedback(self.project,f)
        cfp=s.candidates_fingerprint(self.project)
        s.save(f,dict(base,candidates_fingerprint=cfp,candidate_choice={'selected':'C9'}))
        with self.assertRaisesRegex(ValueError,'Unknown candidate'):
            s.import_feedback(self.project,f)
        s.save(f,dict(base,candidates_fingerprint=cfp))
        s.import_feedback(self.project,f)
        self.assertEqual(s.load(self.project/'reviews'/'human-feedback.json')['candidate_choice']['selected'],'C2')
        (self.project/'candidates.json').unlink()
        with self.assertRaisesRegex(ValueError,'candidates.json is absent'):
            s.import_feedback(self.project,f)

    def test_evidence_url_links_only_http(self):
        evidence=s.load(self.project/'evidence.json')
        evidence['items'][0]['url']='javascript:alert(1)'
        evidence['items'].append({'id':'E2','status':'limited','summary':'linked','source':'fixture','scope':'one','url':' https://example.com/log '})
        s.save(self.project/'evidence.json',evidence)
        story=s.load(self.project/'story.json'); story['beats'][1]['evidence']=['E1','E2']; s.save(self.project/'story.json',story)
        self.assertTrue(any('not http(s)' in w for w in s.audit(self.project)['warnings']))
        html,md=s.write_storyboard(self.project)
        doc=html.read_text()
        self.assertNotIn("href='javascript:",doc)
        self.assertIn('<code>javascript:alert(1)</code>',doc)
        self.assertIn("href='https://example.com/log'",doc)
        self.assertIn('出所: fixture https://example.com/log',md.read_text())

    def test_non_object_files_fail_cleanly(self):
        self.write_candidates()
        s.save(self.project/'reviews'/'ai-candidate-review.json',[])
        s.save(self.project/'reviews'/'ai-story-review.json',[])
        errors=s.audit(self.project)['errors']
        self.assertIn('reviews/ai-candidate-review.json must be a JSON object',errors)
        self.assertIn('reviews/ai-story-review.json must be a JSON object',errors)
        s.write_storyboard(self.project)
        s.save(self.project/'candidates.json',[])
        self.assertIn('candidates.json: candidates must be a list',s.audit(self.project)['errors'])
        s.write_storyboard(self.project)
        s.save(self.project/'brief.json',[])
        with self.assertRaisesRegex(ValueError,'must be JSON objects'):
            s.write_storyboard(self.project)

    def test_board_tolerates_malformed_beat_fields(self):
        story=s.load(self.project/'story.json')
        b1,b2=story['beats']
        b1['role']=['x']; b1['risks']=None; b1['from_previous']=None; b1['next_question']=''
        del b2['claim']
        story['beats'].append('not a beat')
        s.save(self.project/'story.json',story)
        evidence=s.load(self.project/'evidence.json'); evidence['items'][0]['kind']=['x']; evidence['items'][0]['status']={}
        s.save(self.project/'evidence.json',evidence)
        errors=s.audit(self.project)['errors']
        self.assertFalse(any('from_previous' in e or 'risks' in e for e in errors))
        _,md=s.write_storyboard(self.project)
        text=md.read_text()
        self.assertIn('6. 次章へ渡す問い: 未記入',text)
        self.assertIn('2. この章の主張: 未記入',text)

    def test_markdown_has_candidate_and_review_details(self):
        self.write_candidates()
        s.save(self.project/'reviews'/'ai-candidate-review.json',{'fingerprint':s.candidates_fingerprint(self.project),
            'reviewer_independent':True,'recommended':'C1',
            'candidates':[{'candidate_id':'C1','verdict':'ok','strengths':['clear'],'breakpoints':['thin'],
                           'criteria':[{'criterion':'因果関係','assessment':'good'}]}]})
        s.save(self.project/'reviews'/'ai-story-review.json',{'fingerprint':s.fingerprint(self.project),'reviewer_independent':True,
            'findings':[],'audience_takeaway_test':'takeaway ok','missing_proof':['need a baseline']})
        self.assertTrue(any('does not cover candidate C2' in w for w in s.audit(self.project)['warnings']))
        _,md=s.write_storyboard(self.project)
        text=md.read_text()
        for needle in ('独立したコンテキスト: はい','レビュー側の推奨: C1','強み: clear','因果関係: good','- C2: 未記入',
                       '持ち帰りの確認:** takeaway ok','- need a baseline','切り口:'):
            self.assertIn(needle,text)

    def test_checks_duplicate_and_unanswered(self):
        sha=s.fingerprint(self.project)
        row={'check':s.DEFAULT_REVIEW_CHECKS[0],'verdict':'pass','reason':'ok'}
        s.save(self.project/'reviews'/'ai-story-review.json',{'fingerprint':sha,'reviewer_independent':True,'findings':[],'checks':[row,row]})
        report=s.audit(self.project)
        self.assertTrue(any('answered twice' in e for e in report['errors']))
        self.assertTrue(any('not answered by AI review' in w for w in report['warnings']))
        s.save(self.project/'reviews'/'ai-story-review.json',{'fingerprint':sha,'reviewer_independent':True,'findings':[]})
        self.assertFalse(any('not answered' in w for w in s.audit(self.project)['warnings']))

    def test_feedback_rejects_non_string_choice_and_drops_unbound_fingerprint(self):
        self.write_candidates()
        f=Path(self.tmp.name)/'feedback.json'
        base={'fingerprint':s.fingerprint(self.project),'comments':[],'candidates_fingerprint':s.candidates_fingerprint(self.project)}
        for bad in (0,False,[],{},['C1']):
            s.save(f,dict(base,candidate_choice={'selected':bad}))
            with self.assertRaisesRegex(ValueError,'must be strings'):
                s.import_feedback(self.project,f)
        s.save(f,dict(base,candidate_choice={'selected':'C1','instruction':['x']}))
        with self.assertRaisesRegex(ValueError,'must be strings'):
            s.import_feedback(self.project,f)
        s.save(f,base)
        s.import_feedback(self.project,f)
        self.assertNotIn('candidates_fingerprint',s.load(self.project/'reviews'/'human-feedback.json'))

if __name__=='__main__':
    unittest.main()
