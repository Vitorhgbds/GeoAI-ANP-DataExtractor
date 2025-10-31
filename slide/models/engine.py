from slide.models import ModelBuilder


class ModelBuilderEngine(ModelBuilder):

    def build(self):
        
        data = self.collector.collect()
        
        processed_data = self.processor.process(data)
        
        self.model.train(processed_data)
        
        evaluation_results = self.model.evaluate(processed_data)
        
        self.model.save("model_path")
        return evaluation_results