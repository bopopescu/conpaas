<?php
/*
 * Copyright (C) 2010-2011 Contrail consortium.
 *
 * This file is part of ConPaaS, an integrated runtime environment
 * for elastic cloud applications.
 *
 * ConPaaS is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * ConPaaS is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with ConPaaS.  If not, see <http://www.gnu.org/licenses/>.
 */

require_module('ui/page');

class HadoopPage extends ServicePage {

	public function __construct(Service $service) {
		parent::__construct($service);
	}

	public function renderActions() {
		$terminateButton = InputButton('terminate')
			->setId('terminate');
		return $terminateButton;
	}

	protected function renderSubname() {
		$manager = $this->service->getManagerIP();
		return
			'<div class="subname">'.
				$this->renderStateChange().
				' &middot; '.
				LinkUI('namenode', 'http://'.$manager.':50070')
					->setExternal(true).
				' &middot; '.
				LinkUI('job tracker', 'http://'.$manager.':50030')
					->setExternal(true).
			'</div>';
	}
}

?>