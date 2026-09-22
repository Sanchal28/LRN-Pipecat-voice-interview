from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.pipeline.pipeline import Pipeline


class MyProcessor(FrameProcessor):

    async def process_frame(self, frame: Frame, direction):
        print(f"{self.name} received: {type(frame).__name__}")

        await self.push_frame(frame, direction)


processor_1 = MyProcessor(name="First Processor")
processor_2 = MyProcessor(name="Second Processor")

pipeline = Pipeline(
    [
        processor_1,
        processor_2,
    ]
)

print("Pipeline created!")

for processor in pipeline.processors:
    print(f"- {processor.name}")