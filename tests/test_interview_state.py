import unittest

from lrn_interview_agent.interview_state import InterviewState, InterviewStatus
from lrn_interview_agent.bot import question_turn_instruction
from lrn_interview_agent.question_plan import InterviewQuestion, build_question_plan


class InterviewStateTests(unittest.TestCase):
    def test_question_limit_and_transcript_are_application_controlled(self):
        state = InterviewState(max_questions=1)
        state.start()
        self.assertEqual(state.add_question("Walk me through a DCF.", "valuation"), 1)
        state.record_candidate_turn("I would forecast free cash flow.", "2026-09-22T00:00:00Z")
        state.record_interviewer_turn("What discount rate would you use?", "2026-09-22T00:00:01Z")

        with self.assertRaises(RuntimeError):
            state.add_question("A second scored question", "valuation")

        self.assertEqual(state.answers, ["I would forecast free cash flow."])
        self.assertEqual(len(state.transcript), 2)
        self.assertEqual(state.status, InterviewStatus.ACTIVE)

    def test_ib_plan_is_bounded_and_ordered(self):
        plan = build_question_plan("investment_banking_technical", 2)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0].topic, "background")
        self.assertEqual(plan[1].topic, "accounting")

    def test_following_question_requires_a_concrete_acknowledgement(self):
        question = InterviewQuestion("valuation", "How would you value a company?")
        first_turn = question_turn_instruction(1, 6, question)
        later_turn = question_turn_instruction(2, 6, question)

        self.assertNotIn("First acknowledge", first_turn)
        self.assertIn("First acknowledge one concrete detail", later_turn)
        self.assertIn(question.prompt, later_turn)


if __name__ == "__main__":
    unittest.main()
