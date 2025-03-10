# Copyright 2022 The KerasCV Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package="keras_cv")
class MixUp(tf.keras.__internal__.layers.BaseImageAugmentationLayer):
    """MixUp implements the MixUp data augmentation technique.

    Args:
        alpha: Float between 0 and 1.  Inverse scale parameter for the gamma
            distribution.  This controls the shape of the distribution from which the
            smoothing values are sampled.  Defaults 0.2, which is a recommended value
            when training an imagenet1k classification model.
        seed: Integer. Used to create a random seed.

    References:
        [MixUp paper](https://arxiv.org/abs/1710.09412).

    Sample usage:
    ```python
    (images, labels), _ = tf.keras.datasets.cifar10.load_data()
    mixup = keras_cv.layers.preprocessing.mix_up.MixUp(10)
    augmented_images, updated_labels = mixup({'images': images, 'labels': labels})
    # output == {'images': updated_images, 'labels': updated_labels}
    ```
    """

    def __init__(self, alpha=0.2, seed=None, **kwargs):
        super().__init__(seed=seed, **kwargs)
        self.alpha = alpha
        self.seed = seed

    @staticmethod
    def _sample_from_beta(alpha, beta, shape):
        sample_alpha = tf.random.gamma(shape, 1.0, beta=alpha)
        sample_beta = tf.random.gamma(shape, 1.0, beta=beta)
        return sample_alpha / (sample_alpha + sample_beta)

    def _batch_augment(self, inputs):
        images = inputs.get("images", None)
        labels = inputs.get("labels", None)
        if images is None or labels is None:
            raise ValueError(
                "MixUp expects inputs in a dictionary with format "
                '{"images": images, "labels": labels}.'
                f"Got: inputs = {inputs}"
            )
        images, labels = self._update_labels(*self._mixup(images, labels))
        inputs["images"] = images
        inputs["labels"] = labels
        return inputs

    def _augment(self, inputs):
        raise ValueError(
            "MixUp received a single image to `call`.  The layer relies on "
            "combining multiple examples, and as such will not behave as "
            "expected.  Please call the layer with 2 or more samples."
        )

    def _mixup(self, images, labels):
        batch_size = tf.shape(images)[0]
        permutation_order = tf.random.shuffle(tf.range(0, batch_size), seed=self.seed)

        lambda_sample = MixUp._sample_from_beta(self.alpha, self.alpha, (batch_size,))
        lambda_sample = tf.reshape(lambda_sample, [-1, 1, 1, 1])

        mixup_images = tf.gather(images, permutation_order)
        images = lambda_sample * images + (1.0 - lambda_sample) * mixup_images

        return images, labels, tf.squeeze(lambda_sample), permutation_order

    def _update_labels(self, images, labels, lambda_sample, permutation_order):
        labels_for_mixup = tf.gather(labels, permutation_order)

        lambda_sample = tf.reshape(lambda_sample, [-1, 1])
        labels = lambda_sample * labels + (1.0 - lambda_sample) * labels_for_mixup

        return images, labels

    def get_config(self):
        config = {
            "alpha": self.alpha,
            "seed": self.seed,
        }
        base_config = super().get_config()
        return dict(list(base_config.items()) + list(config.items()))
