"""
A Baseline Model.

TfIdfVectorizer + Classify aspects separately
"""
import logging
import numpy as np

from sklearn.metrics import f1_score

from sklearn.pipeline import Pipeline
from sklearn.multioutput import MultiOutputClassifier as MultiOutputClassifier_

from fgclassifier.features import DummyTransform, fm_spec, ensure_named_steps
from fgclassifier.utils import read_data
from fgclassifier import classifiers

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MultiOutputClassifier(MultiOutputClassifier_):
    """MultioutputClassifier with the ability to calculate F1-score
    for each output"""

    def scores(self, X, y):
        """Return f1 score on a test dataset"""
        y_pred = self.predict(X)
        scores = []
        for i, label in enumerate(y.columns):
            score = f1_score(y[label], y_pred[:, i], average='macro')
            scores.append(score)
            logger.debug('  {: <40s}\t{:.4f}'.format(label, score))
        return scores

    def score(self, X, y):
        scores = self.scores(X, y)
        score = np.mean(scores)
        logger.info(' F1 Score: %s', score)
        return score


class Baseline(Pipeline):
    """The Baseline model. Automatically ensuares MultiOutputClassifier

    Parameters
    --------------
        classifier:  the classifier to add to the final step
        name:        name of this model, useful when saving the model
    """

    def __init__(self, classifier, fm=None, steps=None, spec=fm_spec,
                 cache=None, **kwargs):
        if fm is not None:
            if steps is not None:
                raise ValueError('Cannot specify `fm` and `steps` at the same time.')
            steps = [fm]
        else:
            steps = steps or []

        if isinstance(classifier, str) and hasattr(classifiers, classifier):
            classifier = (classifier, getattr(classifiers, classifier))

        # add classifier as the last step
        if classifier is not None:
            steps.append(classifier)

        # Translate coded transformer/classifiers to named pairs
        steps = ensure_named_steps(steps, spec=spec, cache=cache)

        # Make sure last step is a MultiOutputClassifier
        if not isinstance(steps[-1][1], MultiOutputClassifier):
            steps[-1] = (steps[-1][0], MultiOutputClassifier(steps[-1][1]))

        super().__init__(steps, **kwargs)

    @property
    def classifier_name(self):
        return self.steps[-1][0]

    @property
    def fm_name(self):
        """Feature model name"""
        if len(self.steps) > 1:
            return self.steps[-2][0]
        else:
            return 'unknown_fm'

    @property
    def name(self):
        # the second last step is the final step of the transformer
        # we assume it is the basis of feature transformation
        return self.fm_name + '_' + self.classifier_name

    def predict_df(self, df, save_to=None):
        """Make prediction on a data frame and save output"""
        # read_data returns a copy of df
        X, y, df = read_data(df, return_df=True)
        df['content'] = ''
        df[y.columns] = self.predict(X)
        if save_to:
            logger.info(f'Saving predictions to {save_to}...')
            df.to_csv(save_to, encoding="utf_8_sig", index=False)
        return df

    def scores(self, X, y):
        """Scores of all multiple output"""
        Xt = X
        for _, transform in self.steps[:-1]:
            if transform is not None:
                Xt = transform.transform(Xt)
        return self.steps[-1][1].scores(Xt, y)


class Dummy(Baseline):
    """Dummy model"""

    def __init__(self, classifier, **kwargs):
        steps = [
            ('dummy_transform', DummyTransform()),
        ]
        super(Dummy, self).__init__(classifier, steps=steps)

